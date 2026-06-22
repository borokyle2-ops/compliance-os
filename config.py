from pathlib import Path

DB_FILE = Path("data/compliance_os.db")
G20_TARGET = 3.0
G20_WARNING = 5.0
ANOMALY_THRESHOLD = 15.0
REFRESH_HOURS = 6

# DATA SOURCES
WORLD_BANK_URL = "https://remittanceprices.worldbank.org/sites/default/files/rpw_dataset_2011_2025_ql.xlsx"
WORLD_BANK_SHEET = "Dataset (from Q2 2016)"

WISE_API_URL = "https://api.wise.com/v1/rates"
EXCHANGE_RATE_API = "https://open.er-api.com/v6/latest"

# AFRICAN CORRIDORS WE SPECIFICALLY TRACK
AFRICAN_CORRIDORS = [
    ("KEN", "UGA"),  # Kenya - Uganda
    ("KEN", "TZA"),  # Kenya - Tanzania
    ("KEN", "ETH"),  # Kenya - Ethiopia
    ("NGA", "GHA"),  # Nigeria - Ghana
    ("NGA", "KEN"),  # Nigeria - Kenya
    ("ZAF", "ZWE"),  # South Africa - Zimbabwe
    ("ZAF", "MOZ"),  # South Africa - Mozambique
    ("ZAF", "ZMB"),  # South Africa - Zambia
    ("GBR", "NGA"),  # UK - Nigeria (diaspora)
    ("GBR", "KEN"),  # UK - Kenya (diaspora)
    ("USA", "NGA"),  # USA - Nigeria (diaspora)
    ("USA", "KEN"),  # USA - Kenya (diaspora)
    ("UAE", "KEN"),  # UAE - Kenya (Gulf diaspora)
    ("UAE", "ETH"),  # UAE - Ethiopia (Gulf diaspora)
    ("RWA", "KEN"),  # Rwanda - Kenya
    ("UGA", "KEN"),  # Uganda - Kenya
]

# Stablecoin model methodology 
# Source: Estimated from USDC/USDT on-chain settlement data
STABLECOIN_BASE_FEE = 0.05
STABLECOIN_EFFICIENCY_RATIO = 0.12


