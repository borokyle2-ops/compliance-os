import duckdb

DB_PATH = "data/compliance_os.db"

def scan_corridor_anomalies():
    """
    Automated Intelligence Layer: Scans database for pricing anomalies 
    and simulates instant, automated webhook dispatching alerts.
    """

    conn = duckdb.connect(DB_PATH)

    # Query out severe market breaches (> 15% transaction costs)
    anomalies = conn.execute("""
        SELECT corridor_key, total_cost_percent, period
                             FROM fact_corridor_pricing
                             WHERE total_cost_percent > 15.0
                             ORDER BY total_cost_percent DESC
                             LIMIT 3
                             """).fetchall()
    
    conn.close()

    alert_logs = []
    for item in anomalies:
        alert_payload = {
            "event_type": "COMPLIANCE_BREACH_DETECTED",
            "severity": "CRITICAL",
            "corridor": item[0],
            "market_average_cost": f"{item[1]:.2f}%",
            "g20_limit_threshold":"5.00%",
            "reporting_period": item[2]
        }
        alert_logs.append(alert_payload)