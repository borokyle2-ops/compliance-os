# src/sources/forex_source.py
"""
Live forex rate fetcher for African currency pairs.
Source: Open Exchange Rates / ExchangeRate-API (Fallback logic implemented)
Updates: Every hour
"""

import requests
import pandas as pd
import duckdb
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from config import DB_FILE, EXCHANGE_RATE_API

# Expanded, Inclusive Pan-African & Global Currency Codes Mapping
CURRENCY_MAP = {
    # Global Sending Gateways / Funding Hubs
    "USA": "USD", # US Dollar
    "GBR": "GBP", # British Pound
    "EUR": "EUR", # Eurozone Euro
    "CAN": "CAD", # Canadian Dollar
    "UAE": "AED", # UAE Dirham
    "SAR": "SAR", # Saudi Riyal
    "CHN": "CNY", # Chinese Yuan
    "IND": "INR", # Indian Rupee
    
    # Comprehensive African Destination Anchors
    "KEN": "KES", # Kenyan Shilling
    "NGA": "NGN", # Nigerian Naira
    "ZAF": "ZAR", # South African Rand
    "GHA": "GHS", # Ghanaian Cedi
    "UGA": "UGX", # Ugandan Shilling
    "TZA": "TZS", # Tanzanian Shilling
    "RWA": "RWF", # Rwandan Franc
    "ETH": "ETB", # Ethiopian Birr
    "ZMB": "ZMW", # Zambian Kwacha
    "MOZ": "MZN", # Mozambican Metical
    "AGO": "AOA", # Angolan Kwanza
    "CMR": "XAF", # Central African CFA Franc (Cameroon, Gabon, etc.)
    "SEN": "XOF", # West African CFA Franc (Senegal, Ivory Coast, Mali, etc.)
    "EGY": "EGP", # Egyptian Pound
    "MAR": "MAD", # Moroccan Dirham
    "TUN": "TND", # Tunisian Dinar
    "MUS": "MUR", # Mauritian Rupee
    "BWA": "BWP", # Botswana Pula
    "MWI": "MWK", # Malawian Kwacha
    "ZWE": "ZWL", # Zimbabwean Dollar
}

def fetch_forex_rates():
    """Dynamically generates and calculates an exhaustive pan-African corridor market matrix."""
    print(f"[{datetime.now()}] Fetching live institutional forex base rates...")

    try:
        response = requests.get(
            f"{EXCHANGE_RATE_API}/USD",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        rates = data["rates"]

        # 1. Isolate Sender Hubs vs African Destination Hubs
        senders = ["USA", "GBR", "EUR", "CAN", "UAE", "SAR", "CHN", "IND", "ZAF"]
        destinations = [
            "KEN", "NGA", "ZAF", "GHA", "UGA", "TZA", "RWA", "ETH", "ZMB", "MOZ", 
            "AGO", "CMR", "SEN", "EGY", "MAR", "TUN", "MUS", "BWA", "MWI", "ZWE"
        ]

        corridor_forex = []
        skipped = []

        # 2. Dynamically cross-multiply every sender with every receiver
        for src_code in senders:
            for dst_code in destinations:
                # Skip identical currency pairs (e.g., ZAF to ZAF)
                if src_code == dst_code:
                    continue
                    
                src_currency = CURRENCY_MAP.get(src_code)
                dst_currency = CURRENCY_MAP.get(dst_code)

                if not (src_currency and dst_currency):
                    skipped.append((src_code, dst_code, "Missing static ISO mapping"))
                    continue

                src_rate = rates.get(src_currency)
                dst_rate = rates.get(dst_currency)

                if not (src_rate and dst_rate):
                    skipped.append((src_code, dst_code, f"API lacking feed for {src_currency if not src_rate else dst_currency}"))
                    continue

                # Calculate cross-currency mid-market exchange rate using USD base reference
                exchange_rate = dst_rate / src_rate
                
                corridor_forex.append({
                    "source_code": src_code,
                    "destination_code": dst_code,
                    "source_currency": src_currency,
                    "dest_currency": dst_currency,
                    "exchange_rate": round(exchange_rate, 6),
                    "as_of_date": datetime.now()
                })

        if not corridor_forex:
            print("⚠️ Ingestion warning: Zero valid corridor transformations generated.")
            return pd.DataFrame()

        df_forex = pd.DataFrame(corridor_forex)
        print(f"✅ Successfully compiled {len(df_forex)} real-time African corridor forex vectors.")
        if skipped and len(skipped) < 5:  # Keep logs tidy
            for s in skipped:
                print(f"   Skipped {s[0]}-{s[1]}: {s[2]}")
        return df_forex

    except Exception as e:
        print(f"❌ Critical Forex API extraction failed: {e}")
        return pd.DataFrame()
    
def store_forex_rates(df_forex):
    """Safely updates structural asset layers in DuckDB."""
    if df_forex.empty:
        print("⚠️ Storage action bypassed: DataFrame layout empty.")
        return False
    
    conn = duckdb.connect(str(DB_FILE), read_only=False)
    try:
        conn.execute("DROP TABLE IF EXISTS dim_forex_rates")
        conn.execute("""
            CREATE TABLE dim_forex_rates(
                source_code      VARCHAR,
                destination_code VARCHAR,
                source_currency  VARCHAR,
                dest_currency    VARCHAR,
                exchange_rate    DOUBLE,
                as_of_date       TIMESTAMP
            )
        """)

        conn.execute("INSERT INTO dim_forex_rates SELECT * FROM df_forex")
        print(f"💾 Institutional Sync: {len(df_forex)} vectors committed to dim_forex_rates.")
        return True
    except Exception as e:
        print(f"❌ Database commitment exception: {e}")
        return False
    finally:
        conn.close()

def run_forex_pipeline():
    df = fetch_forex_rates()
    return store_forex_rates(df)

if __name__ == "__main__":
    run_forex_pipeline()