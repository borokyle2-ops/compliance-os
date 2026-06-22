# pipeline.py
"""
ComplianceOS Pipeline Runner
Run this to refresh all data sources sequentially:
    python pipeline.py
"""

import sys
import datetime
from pathlib import Path

# Force the project root directory into the Python path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from src.ingestion import run_etl_pipeline
from src.sources.forex_source import run_forex_pipeline
from src.sources.wise_source import run_wise_pipeline

def run_all():
    start = datetime.datetime.now()
    print(f"\n{'='*50}")
    print(f" ComplianceOS Master Pipeline Runner")
    print(f" Started: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    
    results = {}
    
    # 1. Run Master Excel Data Ingestion
    print("[1/3] Syncing Master World Bank Excel Database...")
    results["ingestion"] = run_etl_pipeline()
    
    # 2. Run Live Forex Rates
    print("\n[2/3] Fetching Live Forex Spot Rates...")
    results["forex"] = run_forex_pipeline()
    
    # 3. Run Wise Commercial Fee Structures
    print("\n[3/3] Fetching Wise Commercial Corridor Fees...")
    results["wise"] = run_wise_pipeline()
    
    # Execution Summary Table
    elapsed = (datetime.datetime.now() - start).seconds
    print(f"\n{'='*50}")
    print(f" Pipeline Run Summary (Elapsed: {elapsed}s)")
    print(f"{'='*50}")
    
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {name.upper():<12}: {status}")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    run_all()