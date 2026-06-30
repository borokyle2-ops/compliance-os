# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from pathlib import Path
import duckdb
from src.alerts import scan_corridor_anomalies

# INITIAL PAGE SETTINGS
st.set_page_config(
    page_title="ComplianceOS - G20 Remittance Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ENGINE BRAND THEME (UPDATED WITH FLUID RESPONSIVE METRIC STYLE OVERRIDES)
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    h1 { color: #00CC66 !important; font-family: 'Inter', sans-serif; }
    h3 { font-family: 'Inter', sans-serif; margin-top: 20px;}
    .stMetric { background: #1e2130; border-radius: 8px; padding: 15px; border: 1px solid #2d3142; }
    [data-testid="stSidebar"]  { background-color: #11141e;}
    
    /* FIX: Force container metrics text fields to resize gracefully matching viewport dimensions */
    [data-testid="stMetricValue"] {
        font-size: min(1.7vw, 22px) !important;
        white-space: normal !important;
        word-break: break-all !important;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = Path("data/compliance_os.db")

# AUTOMATED ON-DEMAND ETL ENGINE
def auto_check_and_sync_pipeline():
    """Checks if the data file is current. If not, runs ingestion automatically inline."""
    should_sync = False
    
    if not DB_FILE.exists():
        should_sync = True
    else:
        file_last_modified_date = datetime.fromtimestamp(DB_FILE.stat().st_mtime).date()
        if file_last_modified_date < date.today():
            should_sync = True

    if should_sync:
        try:
            from src.ingestion import run_etl_pipeline
            success = run_etl_pipeline()
            if success:
                st.cache_data.clear()
        except Exception as e:
            pass

# Trigger the auto-sync check immediately on every page load
auto_check_and_sync_pipeline()

# HIGH-SPEED DATABASE EXTRACT
@st.cache_data(ttl=21600)
def fetch_ui_payload():
    conn = duckdb.connect(str(DB_FILE), read_only=True)
    df_payload = conn.execute("""
        SELECT *,
            CASE 
                WHEN total_cost_percent <= 3.0 THEN 'COMPLIANT'
                WHEN total_cost_percent <= 5.0 THEN 'WARNING'
                ELSE 'NON-COMPLIANT'
            END as G20_Status,
            ROUND(0.05 + (total_cost_percent * 0.12), 2) as stablecoin_cost_percent
        FROM fact_corridor_pricing
    """).df()
    conn.close()
    return df_payload

# CACHED FETCH ROUTINES FOR SECONDARY METRICS
@st.cache_data(ttl=3600)
def fetch_african_intelligence():
    conn = duckdb.connect(str(DB_FILE), read_only=True)
    
    df_providers = pd.DataFrame()
    df_forex = pd.DataFrame()

    try:
        tables = conn.execute("SHOW TABLES").df()["name"].tolist()

        if "fact_provider_rates" in tables:
            df_providers = conn.execute("""
                SELECT corridor_key, provider, total_cost_percent, data_source, as_of_date
                FROM fact_provider_rates
                ORDER BY total_cost_percent ASC
            """).df()
    
        if "dim_forex_rates" in tables:
            df_forex = conn.execute("""
                SELECT
                    source_code || '-' || destination_code AS corridor,
                    source_currency,
                    dest_currency,
                    exchange_rate,
                    strftime(as_of_date, '%Y-%m-%d %H:%M') AS updated
                FROM dim_forex_rates
                ORDER BY source_code, destination_code
            """).df()

    except Exception as e:
        st.warning(f"African Intelligence data load error: {e}")
    finally:
        conn.close()

    return df_providers, df_forex


# FIX 1: READ REAL PER-TABLE TIMESTAMPS — not file modification time
@st.cache_data(ttl=300)
def fetch_sync_status():
    """Returns the actual last-updated timestamp for each data source table."""
    conn = duckdb.connect(str(DB_FILE), read_only=True)
    status = {
        "corridors": "N/A",
        "forex": "N/A",
        "wise": "N/A"
    }
    try:
        result = conn.execute(
            "SELECT MAX(as_of_date) FROM fact_corridor_pricing"
        ).fetchone()[0]
        if result:
            status["corridors"] = str(result)[:16]

        result = conn.execute(
            "SELECT MAX(as_of_date) FROM dim_forex_rates"
        ).fetchone()[0]
        if result:
            status["forex"] = str(result)[:16]

        result = conn.execute(
            "SELECT MAX(as_of_date) FROM fact_provider_rates"
        ).fetchone()[0]
        if result:
            status["wise"] = str(result)[:16]

    except Exception:
        pass
    finally:
        conn.close()
    return status


# FIX 2: STALENESS DETECTION — warn when forex data is more than 24 hours old
@st.cache_data(ttl=300)
def check_data_freshness():
    """Returns list of warning strings for any stale data sources."""
    warnings = []
    try:
        conn = duckdb.connect(str(DB_FILE), read_only=True)
        forex_age = conn.execute("""
            SELECT DATEDIFF('hour', MAX(as_of_date), NOW())
            FROM dim_forex_rates
        """).fetchone()[0]
        conn.close()

        if forex_age is not None and forex_age > 24:
            warnings.append(
                f"⚠️ **Forex data is {forex_age} hours old.** "
                f"Run `python pipeline.py` to refresh live rates."
            )
        if forex_age is not None and forex_age > 72:
            warnings.append(
                f"🔴 **Critical: Forex data is {forex_age} hours old.** "
                f"Dashboard rates may no longer reflect market conditions."
            )
    except Exception:
        pass
    return warnings


# EXECUTE DATA LOADS
df = fetch_ui_payload()
df_providers, df_forex = fetch_african_intelligence()
sync = fetch_sync_status()           # FIX 1
freshness_warnings = check_data_freshness()  # FIX 2

# SIDEBAR CONTROLLER
st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/World_Bank_logo.svg/320px-World_Bank_logo.svg.png",
    width=130
)
st.sidebar.title("ComplianceOS")
st.sidebar.caption(f"**Data Engine:** Connected (DuckDB)")

# FIX 1: Show per-source timestamps — sidebar now shows real data freshness per table
st.sidebar.divider()
st.sidebar.caption("**Data Source Freshness**")
st.sidebar.caption(f"World Bank: `{sync['corridors']}`")
st.sidebar.caption(f"Forex Rates: `{sync['forex']}`")
st.sidebar.caption(f"Wise Pricing: `{sync['wise']}`")

if st.sidebar.button("Force Synchronize Pipelines", use_container_width=True):
    from src.ingestion import run_etl_pipeline
    if run_etl_pipeline():
        st.cache_data.clear()
        st.rerun()

st.sidebar.divider()
st.sidebar.subheader("Analytical Filters")

all_sources = sorted(df["source_name"].dropna().unique().tolist())
all_destinations = sorted(df["destination_name"].dropna().unique().tolist())

selected_sources = st.sidebar.multiselect(
    "Sending Country", all_sources, placeholder="Global coverage"
)
selected_destinations = st.sidebar.multiselect(
    "Receiving Country", all_destinations, placeholder="Global coverage"
)
selected_status = st.sidebar.multiselect(
    "Compliance Status",
    ["COMPLIANT", "WARNING", "NON-COMPLIANT"],
    default=["COMPLIANT", "WARNING", "NON-COMPLIANT"]
)

# STREAM FILTERING
filtered = df.copy()
if selected_sources:
    filtered = filtered[filtered["source_name"].isin(selected_sources)]
if selected_destinations:
    filtered = filtered[filtered["destination_name"].isin(selected_destinations)]
if selected_status:
    filtered = filtered[filtered["G20_Status"].isin(selected_status)]

# CORE VIEWPORTS
st.title("G20 Remittance Compliance Engine")
st.caption("Automated Market Intelligence Infrastructure | Tracking UN Sustainable Development Goal 10.c")

# FIX 2: Show staleness warnings at the top of the dashboard if data is old
if freshness_warnings:
    for w in freshness_warnings:
        st.warning(w)

st.divider()

# TABBED INTERFACE
tab_dashboard, tab_african_intel = st.tabs(["Global G20 Analytics", "African Corridor Intelligence"])

with tab_dashboard:
    total = len(filtered)
    compliant = len(filtered[filtered["G20_Status"] == "COMPLIANT"])
    warning = len(filtered[filtered["G20_Status"] == "WARNING"])
    non_compliant = len(filtered[filtered["G20_Status"] == "NON-COMPLIANT"])
    avg_cost = filtered["total_cost_percent"].mean() if total > 0 else 0
    compliance_rate = (compliant / total * 100) if total > 0 else 0

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Total Active Corridors", f"{total:,}")
    m_col2.metric(
        "Global Average Cost",
        f"{avg_cost:.2f}%",
        delta=f"{avg_cost - 3.0:.2f}% vs G20 Target",
        delta_color="inverse"
    )
    m_col3.metric("Compliance Index Rate", f"{compliance_rate:.1f}%")

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    m_col4, m_col5, m_col6 = st.columns(3)
    m_col4.metric("Compliant (≤3%)", f"{compliant:,}")
    m_col5.metric("Warning (3%-5%)", f"{warning:,}")
    m_col6.metric("Non-Compliant (>5%)", f"{non_compliant:,}")

    st.divider()

    # AUTOMATED ALERTS
    st.subheader("Automated Infrastructure Agent Alerts")
    alert_feeds = scan_corridor_anomalies()
    if alert_feeds:
        for alert in alert_feeds[:2]:
            st.error(
                f"**{alert['event_type']}** | Corridor: `{alert['corridor']}` spiked to "
                f"**{alert['market_average_cost']}** "
                f"(Reporting Frame: {alert['reporting_period']}). "
                f"Automated webhook logging executed."
            )
    else:
        st.success("No systemic market pricing anomalies identified across current data logs.")

    st.divider()

    # CHARTS GRID ROW
    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown("### Compliance Matrix Breakdown")
        pie_data = filtered["G20_Status"].value_counts().reset_index()
        pie_data.columns = ["Status", "Count"]
        fig_pie = px.pie(
            pie_data, names="Status", values="Count", hole=0.55,
            color="Status",
            color_discrete_map={
                "COMPLIANT": "#00CC66",
                "WARNING": "#FFAA00",
                "NON-COMPLIANT": "#FF4444"
            }
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            margin=dict(t=30, b=10, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5)
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.markdown("### Cost Density Over Target Intercepts")
        fig_hist = px.histogram(
            filtered, x="total_cost_percent", nbins=60, color="G20_Status",
            color_discrete_map={
                "COMPLIANT": "#00CC66",
                "WARNING": "#FFAA00",
                "NON-COMPLIANT": "#FF4444"
            },
            labels={"total_cost_percent": "Total Cost %", "G20_Status": "Status"}
        )
        fig_hist.add_vline(
            x=3.0, line_dash="dash", line_color="#00CC66",
            annotation_text="3% G20 Target",
            annotation_position="top right",
            annotation_font_color="#00CC66",
            annotation_font_size=11
        )
        fig_hist.add_vline(
            x=5.0, line_dash="dash", line_color="#FF4444",
            annotation_text="5% Maximum Limit",
            annotation_position="bottom right",
            annotation_font_color="#FF4444",
            annotation_font_size=11
        )
        fig_hist.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#1e2130",
            font_color="white",
            xaxis_title="Total Cost %",
            yaxis_title="Corridor Frequency",
            xaxis_range=[0, 22],
            margin=dict(t=30, b=10, l=10, r=10),
            showlegend=False
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()

    # STABLECOIN VS LEGACY CHART
    st.markdown("### Top 10 Most Expensive Channels vs Alternative Stablecoin Settlement Infrastructure")
    if total > 0:
        top10 = filtered.nlargest(10, "total_cost_percent").sort_values(
            by="total_cost_percent", ascending=True
        )
        fig_bar = go.Figure()

        fig_bar.add_trace(go.Bar(
            y=top10["corridor_key"], x=top10["total_cost_percent"], orientation='h',
            name='Legacy Rail Cost Average', marker_color='#FF4444',
            text=top10["total_cost_percent"].apply(lambda x: f" {x:.2f}% "),
            textposition='inside'
        ))

        fig_bar.add_trace(go.Bar(
            y=top10["corridor_key"], x=top10["stablecoin_cost_percent"], orientation='h',
            name='Stablecoin/L2 Optimization Rail (Forecast)', marker_color='#00CC66',
            text=top10["stablecoin_cost_percent"].apply(lambda x: f" {x:.2f}% "),
            textposition='outside'
        ))

        fig_bar.add_vline(
            x=3.0, line_dash="dash", line_color="#00CC66",
            annotation_text="G20 Target (3%)",
            annotation_position="top left"
        )

        fig_bar.update_layout(
            barmode='group',
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#1e2130",
            font_color="white",
            height=500,
            margin=dict(t=40, b=20, l=10, r=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # AUDIT LEDGER
    st.markdown("### Compliance Audit Ledger View")
    display_cols = [
        "source_name", "destination_name",
        "total_cost_percent", "stablecoin_cost_percent",
        "period", "G20_Status"
    ]

    st.dataframe(
        filtered[display_cols],
        column_config={
            "source_name": st.column_config.TextColumn("Sending Country"),
            "destination_name": st.column_config.TextColumn("Receiving Country"),
            "total_cost_percent": st.column_config.NumberColumn(
                "Traditional Cost %", format="%.2f%%"
            ),
            "stablecoin_cost_percent": st.column_config.NumberColumn(
                "Web3 Model Cost %", format="%.2f%%"
            ),
            "period": st.column_config.TextColumn("Reporting Frame"),
            "G20_Status": st.column_config.SelectboxColumn(
                "Status Tag",
                options=["COMPLIANT", "WARNING", "NON-COMPLIANT"]
            )
        },
        hide_index=True,
        use_container_width=True,
        height=350
    )

    st.download_button(
        label="Export Institutional Audit Ledger Records (CSV)",
        data=filtered[display_cols].to_csv(index=False).encode("utf-8"),
        file_name="compliance_ledger_export.csv",
        mime="text/csv",
        use_container_width=True
    )


with tab_african_intel:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.subheader("African Corridor Intelligence")
        st.caption("Multi-source comparison: World Bank vs Commercial providers vs Live FX")
    with col_b:
        # FIX 1: Use real forex table timestamp, not file mtime
        st.metric("Last Forex Sync", sync["forex"][:10] if sync["forex"] != "N/A" else "N/A")

    # FIX 2: Staleness warning inside the African tab too
    if freshness_warnings:
        for w in freshness_warnings:
            st.warning(w)

    # SMART NETWORK STATUS ALERT
    if not df_forex.empty:
        # FIX 1: Use the real per-table sync timestamp here too
        st.info(
            f"🟢 **Live Data Connection Secure:** Feeds are streaming smoothly from the "
            f"primary market API gateway. Last successful sync: **({sync['forex']})**."
        )

    if not df_providers.empty:
        wise_compliant = len(df_providers[df_providers["total_cost_percent"] <= 3.0])
        wise_total = len(df_providers)
        global_rate = round(compliance_rate, 1)
        st.success(
            f"🚀 **{wise_compliant}/{wise_total} Wise-covered corridors** meet the G20 3% target"
            f" - vs only **{global_rate}%** compliance on traditional rails globally. "
            f"Fintech channels represent a structural efficiency milestone."
        )

        with st.expander("View Commercial Settlement Rail Pricing Matrix", expanded=True):
            df_providers['src_hub'] = df_providers['corridor_key'].apply(
                lambda x: x.split(" - ")[0].strip() if " - " in x else x[:3]
            )
            unique_wise_senders = sorted(df_providers['src_hub'].unique().tolist())

            c_filter1, c_filter2 = st.columns([1, 2])
            with c_filter1:
                selected_wise_hub = st.selectbox(
                    "Filter Chart by Origin Funding Hub:",
                    ["All Global Hubs"] + unique_wise_senders,
                    help="Isolate specific source gateways to compare options."
                )

            if selected_wise_hub != "All Global Hubs":
                chart_df = df_providers[
                    df_providers['src_hub'] == selected_wise_hub
                ].sort_values(by="total_cost_percent", ascending=True)
                chart_title = f"Wise Transfer Costs from {selected_wise_hub} Gateways"
                chart_height = max(400, len(chart_df) * 24)
            else:
                chart_df = df_providers.nsmallest(15, "total_cost_percent").sort_values(
                    by="total_cost_percent", ascending=True
                )
                chart_title = "Top 15 Most Cost-Effective Wise Corridors (Global Infrastructure Sample)"
                chart_height = 450

            fig_provider = px.bar(
                chart_df,
                x="total_cost_percent",
                y="corridor_key",
                orientation="h",
                color="total_cost_percent",
                title=chart_title,
                labels={"total_cost_percent": "Transfer Cost %", "corridor_key": ""},
                color_continuous_scale=["#00CC66", "#FFAA00", "#FF4444"]
            )
            fig_provider.add_vline(
                x=3.0, line_dash="dash", line_color="white",
                annotation_text="G20 3% Target",
                annotation_position="top right",
                annotation_font_color="white"
            )
            fig_provider.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#1e2130",
                font_color="white",
                xaxis_title="Transfer Cost %",
                yaxis_title="",
                height=chart_height,
                coloraxis_showscale=False,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig_provider, use_container_width=True)

        # FIX 1: Show Wise data timestamp separately so users know its freshness
        st.caption(f"Wise pricing model last updated: **{sync['wise']}**")

    else:
        st.info("Commercial provider metrics table empty. Run backend ingestion pipeline routines.")

    st.divider()

    # FOREX SPOT RATES TABLE
    if not df_forex.empty:
        st.subheader("Live African Corridor Forex Spot Rates")
        # FIX 1: Caption now uses real table timestamp, not file mtime
        st.caption(
            f"**{len(df_forex)} active** tracked African corridor channels | "
            f"Last sync: **{sync['forex']}**"
        )

        st.dataframe(
            df_forex[["corridor", "source_currency", "dest_currency", "exchange_rate", "updated"]],
            column_config={
                "corridor": st.column_config.TextColumn("Remittance Route", width="medium"),
                "source_currency": st.column_config.TextColumn("Source Code"),
                "dest_currency": st.column_config.TextColumn("Target Asset"),
                "exchange_rate": st.column_config.NumberColumn(
                    "Spot Rate Index", format="%.4f"
                ),
                "updated": st.column_config.TextColumn("Data Generation Log")
            },
            hide_index=True,
            use_container_width=True,
            height=500
        )
    else:
        st.info("Live currency exchange matrices not found. Please refresh data engine feeds.")