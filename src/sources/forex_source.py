# src/sources/forex_source.py
"""
Live forex rate fetcher for African currency pairs.
Source: Open Exchange Rates / ExchangeRate-API (Smart Offline Fallback Implemented)
Updates: Every hour via scheduled pipeline
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
    "CMR": "XAF", # Central African CFA Franc
    "SEN": "XOF", # West African CFA Franc
    "EGY": "EGP", # Egyptian Pound
    "MAR": "MAD", # Moroccan Dirham
    "TUN": "TND", # Tunisian Dinar
    "MUS": "MUR", # Mauritian Rupee
    "BWA": "BWP", # Botswana Pula
    "MWI": "MWK", # Malawian Kwacha
    "ZWE": "ZWL", # Zimbabwean Dollar
}

def is_online():
    """Quick, ultra-low overhead network link validation check."""
    try:
        # Ping Cloudflare's public DNS with a tight 2-second timeout boundary
        requests.get("https://1.1.1.1", timeout=2)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False

def fetch_forex_rates():
    """Dynamically generates an exhaustive market matrix if online, else returns cache trigger."""
    print(f"[{datetime.now()}] Initializing live institutional forex extraction sequence...")

    # PRE-FLIGHT GUARDRAIL: Break execution if internet link is missing
    if not is_online():
        print("⚠️ Device is Offline. Aborting API network calls to preserve data and power metrics.")
        return "USE_CACHE"

    try:
        response = requests.get(
            f"{EXCHANGE_RATE_API}/USD",
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        rates = data.get("rates") or data.get("conversion_rates")

        if not rates:
            return "USE_CACHE"

        # 1. Isolate Sender Hubs vs African Destination Hubs
        senders = ["USA", "GBR", "EUR", "CAN", "UAE", "SAR", "CHN", "IND", "ZAF"]
        destinations = [
            "KEN", "NGA", "ZAF", "GHA", "UGA", "TZA", "RWA", "ETH", "ZMB", "MOZ", 
            "AGO", "CMR", "SEN", "EGY", "MAR", "TUN", "MUS", "BWA", "MWI", "ZWE"
        ]

        corridor_forex = []

        # 2. Dynamically cross-multiply every sender with every receiver
        for src_code in senders:
            for dst_code in destinations:
                if src_code == dst_code:
                    continue
                    
                src_currency = CURRENCY_MAP.get(src_code)
                dst_currency = CURRENCY_MAP.get(dst_code)

                if not (src_currency and dst_currency):
                    continue

                src_rate = rates.get(src_currency)
                dst_rate = rates.get(dst_currency)

                if not (src_rate and dst_rate):
                    continue

                # Calculate cross-currency mid-market exchange rate using USD base reference
                exchange_rate = float(dst_rate) / float(src_rate)
                
                corridor_forex.append({
                    "source_code": src_code,
                    "destination_code": dst_code,
                    "source_currency": src_currency,
                    "dest_currency": dst_currency,
                    "exchange_rate": round(exchange_rate, 6),
                    "as_of_date": datetime.now(),
                    "status": "Live Feed"  # Explicit health state metric
                })

        if not corridor_forex:
            return "USE_CACHE"

        df_forex = pd.DataFrame(corridor_forex)
        print(f"Successfully compiled {len(df_forex)} real-time African corridor forex vectors.")
        return df_forex

    except Exception as e:
        print(f"⚠️ Primary Forex API cluster unreachable ({e}). Fallback to local cache cache enabled.")
        return "USE_CACHE"
    
def store_forex_rates(df_forex):
    """Safely updates relational layers in DuckDB without bloating binary file sizing."""
    conn = duckdb.connect(str(DB_FILE), read_only=False)
    try:
        # ---- OFFLINE HANDLING CRITERIA ----
        if isinstance(df_forex, str) and df_forex == "USE_CACHE":
            print("Graceful Fallback: System offline. Preserving historical data points.")
            
            # Check if database schema exists before updating status fields
            table_check = conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = 'dim_forex_rates'"
            ).fetchone()[0]
            
            if table_check > 0:
                conn.execute("UPDATE dim_forex_rates SET status = 'Cached (Offline Mode)'")
                print("🏁 Data status successfully transitioned to Offline Mode.")
            return True
            
        # ---- ONLINE RUNTIME CRITERIA ----
        if df_forex.empty:
            print("Storage action bypassed: DataFrame layout empty.")
            return False

        conn.execute("DROP TABLE IF EXISTS dim_forex_rates")
        conn.execute("""
            CREATE TABLE dim_forex_rates(
                source_code      VARCHAR,
                destination_code VARCHAR,
                source_currency  VARCHAR,
                dest_currency    VARCHAR,
                exchange_rate    DOUBLE,
                as_of_date       TIMESTAMP,
                status           VARCHAR
            )
        """)

        conn.execute("INSERT INTO dim_forex_rates SELECT * FROM df_forex")
        print(f"Institutional Sync: {len(df_forex)} vectors committed to dim_forex_rates.")
        return True
    except Exception as e:
        print(f"Database commitment exception: {e}")
        return False
    finally:
        conn.close()

def run_forex_pipeline():
    df = fetch_forex_rates()
    return store_forex_rates(df)

if __name__ == "__main__":
    run_forex_pipeline()