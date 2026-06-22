# src/pipeline.py
"""
Master Pipeline Orchestrator
Runs all data sources in sequence and logs results.
"""

import logging
from datetime import datetime
from pathlib import Path

# Configure Logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    filename = "logs/pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def run_all_pipelines():
    """Run all data source pipelines in order."""
    results = {}
    start = datetime.now()
    logging.info("="*50)
    logging.info("Master Pipeline Started")

    #1. World Bank (primary source)
    try:
        from src.ingestion import run_etl_pipeline
        results["world_bank"] = run_etl_pipeline()
        logging.info(f"World Bank:{'SUCCESS' if results['world_bank']else 'FAILED'}")
    except Exception as e:
        results["world_bank"] = False
        logging.error(f"World Bank pipeline error: {e}")
    #2. Forex rates (real-time)
    try:
        from src.sources.forex_source import run_forex_pipeline
        results["forex"] = run_forex_pipeline()
        logging.info(f"Forex Rates: {'SUCCESS' if results['forex'] else 'FAILED'}")
    except Exception as e:
        results["forex"] = False
        logging.error(f"Forex pipeline error: {e}")
    #3. Wise rates (commercial)
    try:
        from src.sources.wise_source import run_wise_pipeline
        results["wise"] = run_wise_pipeline()
        logging.info(f"Wise Rates: {'SUCCESS' if results['wise'] else 'FAILED'}")
    except Exception as e:
        results["wise"] = False
        logging.error(f"Wise pipeline error: {e}")

    # Summary
    duration = (datetime.now() - start).seconds
    success_count = sum(results.values())
    total_count = len(results)

    logging.info(f"Pipeline Complete: {success_count}/{total_count} sources succeeded in {duration}s")
    logging.info("="*50)

    return results

if __name__ == "__main__":
    results = run_all_pipelines()
    print("\nPipeline Results:")
    for source, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f" {source:15} {status}")
        
           

