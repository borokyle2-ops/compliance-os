# api.py
from fastapi import FastAPI, HTTPException
import duckdb
from pathlib import Path

app = FastAPI(
    title="ComplianceOS Data Core API",
    description="Automated Institutional Market Intelligence Grid | Tracking UN SDG 10.c",
    version="1.1"
)

DB_FILE = Path("data/compliance_os.db")

@app.get("/")
def read_root():
    return {
        "status": "ONLINE",
        "engine": "DuckDB Analytics Core",
        "endpoints_available": [
            "/api/v1/rates/live-forex",
            "/api/v1/costs/commercial-providers",
            "/api/v1/corridor/{source_currency}/{dest_currency}"
        ]
    }

@app.get("/api/v1/rates/live-forex")
def get_live_forex():
    """Extracts all active live market forex spot rates from the database grid."""
    if not DB_FILE.exists():
        raise HTTPException(status_code=500, detail="Analytical database footprint missing.")
    
    conn = duckdb.connect(str(DB_FILE), read_only=True)
    try:
        df = conn.execute("""
            SELECT 
                source_code || ' → ' || destination_code as corridor,
                source_currency, dest_currency, exchange_rate,
                strftime(as_of_date, '%Y-%m-%d %H:%M') as updated_at
            FROM dim_forex_rates
        """).df()
        return {"count": len(df), "data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database extraction failed: {str(e)}")
    finally:
        conn.close()

@app.get("/api/v1/costs/commercial-providers")
def get_provider_costs():
    """Extracts processed transaction costs and pricing across commercial settlement rails."""
    conn = duckdb.connect(str(DB_FILE), read_only=True)
    try:
        df = conn.execute("SELECT * FROM fact_provider_rates").df()
        return {"count": len(df), "data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()