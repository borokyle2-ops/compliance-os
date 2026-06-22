import pandas as pd
import duckdb
import requests
import datetime
from pathlib import Path

DATA_URL = "https://remittanceprices.worldbank.org/sites/default/files/rpw_dataset_2011_2025_q1.xlsx"
DB_DIR = Path("data")
DB_FILE = DB_DIR / "compliance_os.db"
SHEET_NAME = "Dataset (from Q2 2016)"


def initialize_schema(conn):
    """Create all required tables if they don't exist."""
    print("Initializing database schema...")
    
    # Main World Bank Corridor Pricing Tablw
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fact_corridor_pricing (
            source_code         VARCHAR,
            source_name         VARCHAR,
            destination_code    VARCHAR,
            destination_name    VARCHAR,
            total_cost_percent  DOUBLE,
            period              VARCHAR,
            corridor_key        VARCHAR,
            as_of_date          TIMESTAMP
        )
    """)

    # Wise + Future Commercial Provider Rates Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fact_provider_rates (
            source_code         VARCHAR,
            destination_code    VARCHAR,
            source_currency     VARCHAR,
            dest_currency       VARCHAR,
            provider            VARCHAR,
            total_cost_percent  DOUBLE,
            send_amount         DOUBLE,
            currency            VARCHAR,
            corridor_key        VARCHAR,
            data_source         VARCHAR,
            as_of_date          TIMESTAMP
        )
    """)

    # Live Forex Spot Rates Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dim_forex_rates (
            source_code         VARCHAR,
            destination_code    VARCHAR,
            source_currency     VARCHAR,
            dest_currency       VARCHAR,
            exchange_rate       DOUBLE,
            as_of_date          TIMESTAMP
        )
    """)

    print("Schema initialized: 3 tables ready.")

    
def run_etl_pipeline():
    print(f"[{datetime.datetime.now()}] Intializing Ingestion Pipeline")
    DB_DIR.mkdir(exist_ok=True)

    try:
        # Always initialize schema first so other pipelines do not fail
        conn = duckdb.connect(str(DB_FILE), read_only=False)
        initialize_schema(conn)

        print("Loading corridor data...")
        df_raw = pd.read_excel("corridor_data.xlsx", sheet_name=SHEET_NAME)
        print(f"Loaded {len(df_raw)} rows from local file.")


        # Clean up column names
        df_raw.columns = df_raw.columns.str.strip()
        cost_col = "cc2 total cost %"

        df_raw["clean_cost"] = pd.to_numeric(df_raw[cost_col], errors="coerce")
        df_raw = df_raw.dropna(subset=["clean_cost","source_name", "destination_name"])

        # FIXING THE BUG: Group by unique corridors to get the TRUE MEAN cost
        # This collapses the 197,999 historical entries into distinct geographical lines
        df_clean = df_raw.groupby(["source_code", "source_name", "destination_code", "destination_name"]).agg({"clean_cost": "mean", "period": "last"}).reset_index()

        df_clean["corridor_key"] = df_clean["source_name"] + "->" + df_clean["destination_name"]
        df_clean["as_of_date"] = datetime.datetime.now()

        #Write data cleanly to our optimized database store
        conn.execute("DROP TABLE IF EXISTS fact_corridor_pricing")
        conn.execute("""
            CREATE TABLE fact_corridor_pricing (
                     source_code VARCHAR,
                     source_name VARCHAR,
                     destination_code VARCHAR,
                     destination_name VARCHAR,
                     total_cost_percent DOUBLE,
                     period VARCHAR,
                     corridor_key VARCHAR,
                     as_of_date TIMESTAMP
                  )
            """)
        
        conn.execute("INSERT INTO fact_corridor_pricing SELECT * FROM df_clean")
        conn.close()

        print(f"Success: {len(df_clean)} unique corridors stored in DuckDB.")
        return True
    
    except Exception as e:
        print(f"Critical Pipeline Failure: {e}")
        return False
    
if __name__ == "__main__":
        run_etl_pipeline()
        