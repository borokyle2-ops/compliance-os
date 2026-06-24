# ComplianceOS — G20 Remittance Compliance Engine

> Automated Market Intelligence Infrastructure | Tracking UN Sustainable Development Goal 10.c

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)](https://streamlit.io)
[![DuckDB](https://img.shields.io/badge/DuckDB-Embedded-yellow)](https://duckdb.org)
[![Data](https://img.shields.io/badge/Data-World%20Bank%20%7C%20Live%20FX%20%7C%20Wise-green)]()
[![License](https://img.shields.io/badge/License-MIT-white)]()

---

## What Is ComplianceOS?

ComplianceOS is a multi-source remittance compliance intelligence dashboard that tracks whether global money transfer corridors meet the G20's SDG 10.c target of reducing remittance costs to 3% or below by 2030.

It pulls from three independent data sources, normalizes them into a single DuckDB analytical layer, and surfaces compliance insights across 377 World Bank corridors, 179 live forex vectors, and 160 commercial provider pricing records — all in a single Streamlit interface.

---

## The Problem It Solves

The global average remittance cost is **4.65%** — 1.65 percentage points above the G20 target. Only **23.6%** of tracked corridors are compliant. African corridors are disproportionately expensive, with some exceeding 15%.

ComplianceOS makes this data visible, filterable, and exportable — the kind of infrastructure that compliance analysts, fintech operators, and policy researchers need but rarely have in one place.

---

## Architecture

```
ComplianceOS/
├── app.py                  # Streamlit dashboard — all UI logic
├── pipeline.py             # One-command data refresh runner
├── config.py               # Corridor definitions & constants
├── requirements.txt        # Python dependencies
├── src/
│   ├── ingestion.py        # World Bank ETL + schema initialization
│   ├── alerts.py           # Anomaly detection engine
│   └── sources/
│       ├── forex_source.py # Live FX rates — 9 senders × 20 African destinations
│       └── wise_source.py  # Wise commercial pricing model — 160 corridors
├── data/                   # Generated at runtime — not in version control
└── logs/                   # Pipeline run logs — not in version control
```

### Data Flow

```
World Bank Excel  →  ingestion.py   →  fact_corridor_pricing  (377 corridors)
ExchangeRate-API  →  forex_source.py →  dim_forex_rates        (179 live vectors)
Wise Pricing Model → wise_source.py  →  fact_provider_rates    (160 estimates)
                              ↓
                    DuckDB (compliance_os.db)
                              ↓
                    Streamlit Dashboard (app.py)
```

---

## Data Sources

| Source | DuckDB Table | Coverage | Update Frequency |
|--------|-------------|----------|-----------------|
| World Bank Remittance Prices Worldwide | `fact_corridor_pricing` | 377 global corridors | Quarterly |
| ExchangeRate-API (open tier) | `dim_forex_rates` | 179 African corridor vectors | Hourly |
| Wise Regional Pricing Model | `fact_provider_rates` | 160 send-to-Africa estimates | Daily |

### Important Note on Wise Data

`wise_source.py` generates cost **estimates** based on Wise's published regional fee tiers (sourced from wise.com/pricing). It is **not** connected to the Wise live API.

- **Verified published rates** are used for high-volume corridors: USD→KES, GBP→KES, USD→NGN, GBP→NGN
- **Regional baseline estimates** are used for all other corridors, derived from Wise's published fee structure tiers for East Africa, West Africa, Southern Africa, and North Africa
- All records are labelled `data_source: "Wise Corporate Pricing Schedule"` in the database

This is an estimation model for research and portfolio purposes — not a live commercial feed.

---

## Dashboard Sections

### Tab 1: Global G20 Analytics
- **KPI Metrics** — Total corridors, global average cost, compliance index rate
- **Status Breakdown** — Compliant (≤3%), Warning (3–5%), Non-Compliant (>5%)
- **Automated Alerts** — Anomaly detection across current data logs
- **Compliance Matrix** — Donut chart by G20 status
- **Cost Density Histogram** — Corridor frequency vs total cost % with target intercepts
- **Stablecoin Comparison** — Top 10 most expensive corridors vs Web3 settlement model forecast
- **Compliance Audit Ledger** — Full filterable table with CSV export

### Tab 2: African Corridor Intelligence
- **Live Feed Status** — Data connection health indicator with last sync timestamp
- **Compliance Callout** — Wise fintech rails vs traditional rails comparison
- **Commercial Provider Chart** — Transfer cost % by corridor with G20 3% target line
- **Live Forex Spot Rates** — 179 real-time corridor vectors (9 global senders × 20 African destinations)

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- Windows / Mac / Linux
- Internet connection (for live data pipelines)

### 1. Clone the Repository

```bash
git clone https://github.com/[your-username]/ComplianceOS.git
cd ComplianceOS
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows (Command Prompt)
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download World Bank Data

Download the Remittance Prices Worldwide dataset from:
```
https://remittanceprices.worldbank.org/sites/default/files/rpw_dataset_2011_2025_q1.xlsx
```
Save it as `corridor_data.xlsx` in the project root directory.

### 5. Initialize Database & Run Pipelines

```bash
# Initialize schema + load World Bank corridor data
python -c "import sys; sys.path.insert(0,'.'); from src.ingestion import run_etl_pipeline; run_etl_pipeline()"

# Run all three data pipelines
python pipeline.py
```

### 6. Launch Dashboard

```bash
streamlit run app.py
```

Dashboard opens at `http://localhost:8501`

---

## Refreshing Data

```bash
# Runs ingestion + forex + Wise pipelines in sequence
python pipeline.py
```

For automated refresh on Windows, schedule `refresh.bat` via Task Scheduler to run every 6 hours.

---

## G20 Compliance Logic

The G20 set a target under UN SDG 10.c to reduce the global average cost of remittances to 3% by 2030, with no corridor exceeding 5%.

| Status | Cost Threshold | Current Count |
|--------|---------------|---------------|
| ✅ Compliant | ≤ 3.0% | 89 corridors (23.6%) |
| ⚠️ Warning | 3.0% – 5.0% | 158 corridors (41.9%) |
| ❌ Non-Compliant | > 5.0% | 130 corridors (34.5%) |

**Global average: 4.65%** — 1.65pp above target as of Q1 2025.

---

## Stablecoin / Web3 Model Methodology

The stablecoin cost forecast column uses a flat-network efficiency model:

```
stablecoin_cost = 0.05 + (traditional_cost × 0.12)
```

Derived from estimated USDC/USDT on-chain settlement benchmarks. This represents a theoretical optimization model, not a live product rate.

Configured in `config.py`:
```python
STABLECOIN_BASE_FEE = 0.05
STABLECOIN_EFFICIENCY_RATIO = 0.12
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Dashboard | Streamlit |
| Database | DuckDB (embedded, file-based) |
| Data Processing | Pandas |
| Visualizations | Plotly Express + Plotly Graph Objects |
| ETL Pipeline | Python (requests, openpyxl) |
| Scheduling | Windows Task Scheduler / cron |
| Language | Python 3.13 |

---

## Key Findings

- **377 corridors tracked** across G20 World Bank reporting data
- **Only 23.6% meet the G20 3% target** — the majority of global remittance flows remain non-compliant
- **Angola → Namibia costs 15.50%** — the most expensive tracked African intra-regional corridor
- **Tanzania → Kenya costs 15.29%** on legacy rails — Wise regional estimate: 0.858%
- **All 160 Wise-modelled corridors fall below 2%** — fintech rails are structurally more cost-efficient than legacy correspondent banking infrastructure
- **179 live forex vectors** tracked in real time across 9 global funding hubs and 20 African destination markets

---

## Author

**Simon Boro Kiarii**
Operations & Fintech Compliance Analyst | Nairobi, Kenya

[LinkedIn](https://linkedin.com/in/[your-handle]) · [GitHub](https://github.com/[your-username])

Built as part of a fintech engineering and compliance transition portfolio — combining operational analytics, AML/CFT frameworks, and payment infrastructure intelligence.

---

## License

MIT License — see `LICENSE` for details.

---

## Disclaimer

This dashboard is built for research, educational, and portfolio demonstration purposes.

- **World Bank data** is used under their open data license
- **Wise pricing estimates** are derived from publicly available fee schedules and do not represent official Wise pricing or a live API connection
- **Exchange rates** are sourced from a free-tier API and may not reflect real-time institutional pricing
- **Stablecoin cost figures** are forecast models, not live product rates

This tool does not constitute financial or compliance advice.
