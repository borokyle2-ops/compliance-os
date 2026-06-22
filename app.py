# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import duckdb
from src.alerts import scan_corridor_anomalies

# INITIAL PAGE SETTINGS
st.set_page_config(
    page_title="ComplianceOS - G20 Remittance Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ENGINE BRAND THEME
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    h1 { color: #00CC66 !important; font-family: 'Inter', sans-serif; }
    h3 { font-family: 'Inter', sans-serif; margin-top: 20px;}
    .stMetric { background: #1e2130; border-radius: 8px; padding: 15px; border: 1px solid #2d3142; }
    [data-testid="stSidebar"]  { background-color: #11141e;}
</style>
""", unsafe_allow_html=True)

DB_FILE = Path("data/compliance_os.db")

# ENFORCE DATA ENGINE SAFETY VALVE
if not DB_FILE.exists():
    st.error("Analytical database footprint missing. Please run 'python src/ingestion.py' in your terminal first.")
    st.stop()

# HIGH-SPEED DATABASE EXTRACT
@st.cache_data(ttl=300) # Caches results for 5 minutes
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
@st.cache_data(ttl=300)
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
                    strftime(as_of_date, '%Y-%m-%d %H:%M') AS updated,
                    status
                FROM dim_forex_rates
                ORDER BY source_code, destination_code
            """).df()

    except Exception as e:
        st.warning(f"African Intelligence data load error: {e}")
    finally:
        conn.close()

    return df_providers, df_forex    


# EXECUTE DATA LOADS
df = fetch_ui_payload()
df_providers, df_forex = fetch_african_intelligence()

mtime = DB_FILE.stat().st_mtime
last_updated = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

# SIDEBAR CONTROLLER (CLEAN FILTERS WORKSPACE)
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/World_Bank_logo.svg/320px-World_Bank_logo.svg.png", width=130)
st.sidebar.title("ComplianceOS")
st.sidebar.caption(f"**Data Engine:** Connected (DuckDB)")
st.sidebar.caption(f"**Sync Date:** {last_updated}")

if st.sidebar.button("Force Synchronize Pipelines", use_container_width=True):
    from src.ingestion import run_etl_pipeline
    if run_etl_pipeline():
        st.cache_data.clear()
        st.rerun()

st.sidebar.divider()
st.sidebar.subheader("Analytical Filters")

all_sources = sorted(df["source_name"].dropna().unique().tolist())
all_destinations = sorted(df["destination_name"].dropna().unique().tolist())

selected_sources = st.sidebar.multiselect("Sending Country", all_sources, placeholder="Global coverage")
selected_destinations = st.sidebar.multiselect("Receiving Country", all_destinations, placeholder="Global coverage")
selected_status = st.sidebar.multiselect("Compliance Status", ["COMPLIANT", "WARNING", "NON-COMPLIANT"], default=["COMPLIANT", "WARNING", "NON-COMPLIANT"])

# STREAM FILTERING RUNTIMES
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
st.divider()

# TABBED INTERFACE ARCHITECTURE FOR CLEAN REAL ESTATE
tab_dashboard, tab_african_intel = st.tabs(["Global G20 Analytics", "African Corridor Intelligence"])

with tab_dashboard:
    # RESPONSIVE GRID LAYOUT FOR KPI METRICS
    total = len(filtered)
    compliant = len(filtered[filtered["G20_Status"] == "COMPLIANT"])
    warning = len(filtered[filtered["G20_Status"] == "WARNING"])
    non_compliant = len(filtered[filtered["G20_Status"] == "NON-COMPLIANT"])
    avg_cost = filtered["total_cost_percent"].mean() if total > 0 else 0
    compliance_rate = (compliant / total * 100) if total > 0 else 0

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Total Active Corridors", f"{total:,}")
    m_col2.metric("Global Average Cost", f"{avg_cost:.2f}%", delta=f"{avg_cost - 3.0:.2f}% vs G20 Target", delta_color="inverse")
    m_col3.metric("Compliance Index Rate", f"{compliance_rate:.1f}%")

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    m_col4, m_col5, m_col6 = st.columns(3)
    m_col4.metric("Compliant (≤3%)", f"{compliant:,}")
    m_col5.metric("Warning (3%-5%)", f"{warning:,}")
    m_col6.metric("Non-Compliant (>5%)", f"{non_compliant:,}")

    st.divider()

    # INTEGRATED AUTOMATED ALERTS PREVIEW WINDOW
    st.subheader("Automated Infrastructure Agent Alerts")
    alert_feeds = scan_corridor_anomalies()
    if alert_feeds:
        for alert in alert_feeds[:2]:
            st.error(f"**{alert['event_type']}** | Corridor: `{alert['corridor']}` spiked to **{alert['market_average_cost']}** (Reporting Frame: {alert['reporting_period']}). Automated webhook logging executed.")
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
             color="Status", color_discrete_map={"COMPLIANT": "#00CC66", "WARNING": "#FFAA00", "NON-COMPLIANT": "#FF4444"}
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
             color_discrete_map={"COMPLIANT": "#00CC66", "WARNING": "#FFAA00", "NON-COMPLIANT": "#FF4444"},
             labels={"total_cost_percent": "Total Cost %", "G20_Status": "Status"}
         )
         
         fig_hist.add_vline(x=3.0, line_dash="dash", line_color="#00CC66", 
                            annotation_text="3% G20 Target", annotation_position="top right", 
                            annotation_font_color="#00CC66", annotation_font_size=11)
         
         fig_hist.add_vline(x=5.0, line_dash="dash", line_color="#FF4444", 
                            annotation_text="5% Maximum Limit", annotation_position="bottom right", 
                            annotation_font_color="#FF4444", annotation_font_size=11)
         
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

    # HORIZONTAL BAR GRID CHART: OPTIMIZED WEB3 VS LEGACY CHANNEL PRICING
    st.markdown("### Top 10 Most Expensive Channels vs Alternative Stablecoin Settlement Infrastructure")
    if total > 0:
       top10 = filtered.nlargest(10, "total_cost_percent").sort_values(by="total_cost_percent", ascending=True)
       fig_bar = go.Figure()
    
       # Trace 1: Legacy Traditional Cost Average
       fig_bar.add_trace(go.Bar(
            y=top10["corridor_key"], x=top10["total_cost_percent"], orientation='h',
            name='Legacy Rail Cost Average', marker_color='#FF4444',
            text=top10["total_cost_percent"].apply(lambda x: f" {x:.2f}% "), textposition='inside'
       ))
    
       # Trace 2: Next-Gen Web3 Forecast Cost
       fig_bar.add_trace(go.Bar(
            y=top10["corridor_key"], x=top10["stablecoin_cost_percent"], orientation='h',
            name='Stablecoin/L2 Optimization Rail (Forecast)', marker_color='#00CC66',
            text=top10["stablecoin_cost_percent"].apply(lambda x: f" {x:.2f}% "), textposition='outside'
       ))
    
       fig_bar.add_vline(x=3.0, line_dash="dash", line_color="#00CC66", 
                         annotation_text="G20 Target (3%)", annotation_position="top left")
       
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

    # GRANULAR REGULATORY AUDIT LEDGER
    st.markdown("### Compliance Audit Ledger View")
    display_cols = ["source_name", "destination_name", "total_cost_percent", "stablecoin_cost_percent", "period", "G20_Status"]
    
    st.dataframe(
        filtered[display_cols],
        column_config={
            "source_name": st.column_config.TextColumn("Sending Country"),
            "destination_name": st.column_config.TextColumn("Receiving Country"),
            "total_cost_percent": st.column_config.NumberColumn("Traditional Cost %", format="%.2f%%"),
            "stablecoin_cost_percent": st.column_config.NumberColumn("Web3 Model Cost %", format="%.2f%%"),
            "period": st.column_config.TextColumn("Reporting Frame"),
            "G20_Status": st.column_config.SelectboxColumn("Status Tag", options=["COMPLIANT", "WARNING", "NON-COMPLIANT"])
        },
        hide_index=True, 
        use_container_width=True, 
        height=350
    )

    # EXPORT TRIGGERS
    st.download_button(
        label="Export Institutional Audit Ledger Records (CSV)",
        data=filtered[display_cols].to_csv(index=False).encode("utf-8"),
        file_name="compliance_ledger_export.csv", mime="text/csv", use_container_width=True
    )

with tab_african_intel:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.subheader("African Corridor Intelligence")
        st.caption("Multi-source comparison: World Bank vs Commercial providers vs Live FX")
    with col_b:
        if not df_forex.empty:
            st.metric("Last Data Sync", df_forex["updated"].iloc[0][:10])
      
    # SMART OFFLINE NETWORK STATUS ALERT SYSTEM
    if not df_forex.empty:
        network_status = df_forex["status"].iloc[0]
        sync_timestamp = df_forex["updated"].iloc[0]
        if "Cached" in network_status:
            st.warning(f"⚠️ **Network Interrupted - Operating in Offline Mode:** Displaying cached market indices from your last successful sync ({sync_timestamp}). The pipeline will resume live streaming as soon as your device connects to the internet.")
        else:
            st.info(f"🟢 **Live Data Connection Secure:** Feeds are streaming smoothly from the primary market API gateway.")

    if not df_providers.empty:
        wise_compliant = len(df_providers[df_providers["total_cost_percent"] <= 3.0])
        wise_total = len(df_providers)
        global_rate = round(compliance_rate, 1)
        st.success(
            f"🚀 **{wise_compliant}/{wise_total} Wise-covered corridors** meet the G20 3% target"
            f" - vs only **{global_rate}%** compliance on traditional rails globally. "
            f"Fintech channels represent a structural efficiency milestone."
        )
        
        # DYNAMIC ACCORDION WORKSPACE FOR COMMERCIAL DATA
        with st.expander("View Commercial Settlement Rail Pricing Matrix", expanded=True):
            df_providers['src_hub'] = df_providers['corridor_key'].apply(lambda x: x.split(" - ")[0].strip() if " - " in x else x[:3])
            unique_wise_senders = sorted(df_providers['src_hub'].unique().tolist())
            
            c_filter1, c_filter2 = st.columns([1, 2])
            with c_filter1:
                selected_wise_hub = st.selectbox(
                    "Filter Chart by Origin Funding Hub:", 
                    ["All Global Hubs"] + unique_wise_senders,
                    help="Isolate specific source gateways to compare options clear of layout noise."
                )
            
            if selected_wise_hub != "All Global Hubs":
                chart_df = df_providers[df_providers['src_hub'] == selected_wise_hub].sort_values(by="total_cost_percent", ascending=True)
                chart_title = f"Wise Transfer Costs originating from {selected_wise_hub} Gateways"
                chart_height = max(400, len(chart_df) * 24)
            else:
                chart_df = df_providers.nsmallest(15, "total_cost_percent").sort_values(by="total_cost_percent", ascending=True)
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
            fig_provider.add_vline(x=3.0, line_dash="dash", line_color="white", annotation_text="G20 3% Target", annotation_position="top right", annotation_font_color="white")
            
            fig_provider.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#1e2130",
                font_color="white",
                xaxis_title="Transfer Cost %",
                yaxis_title="",
                height=chart_height,
                coloraxis_showscale=False,
                yaxis={'categoryorder':'total ascending'}
            )
            st.plotly_chart(fig_provider, use_container_width=True)
    else:
        st.info("Commercial provider metrics table empty. Run backend ingestion pipeline routines.")

    st.divider()

    # HIGH-PERFORMANCE FORMATTED FOREX GRID VIEW
    if not df_forex.empty:
        st.subheader("Live African Corridor Forex Spot Rates")
        last_sync = df_forex["updated"].iloc[0] if not df_forex.empty else "N/A"
        st.caption(f"**{len(df_forex)} active** tracked African corridor channels | Last sync: **{last_sync}**")

        # INTERACTIVE DATA GRID WITH FORMATTED FOREX DATA
        st.dataframe(
            df_forex[["corridor", "source_currency", "dest_currency", "exchange_rate", "updated", "status"]],
            column_config={
                "corridor": st.column_config.TextColumn("Remittance Route", width="medium"),
                "source_currency": st.column_config.TextColumn("Source Code"),
                "dest_currency": st.column_config.TextColumn("Target Asset"),
                "exchange_rate": st.column_config.NumberColumn("Spot Rate Index", format="%.4f"),
                "updated": st.column_config.TextColumn("Data Generation Log"),
                "status": st.column_config.TextColumn("Network Feed Status"),
            },
            hide_index=True,
            use_container_width=True,
            height=500
        )
    else:
        st.info("Live currency exchange matrices not found. Please refresh data engine feeds.")