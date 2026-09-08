import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
import streamlit as st

# 1. Page Layout Configuration
st.set_page_config(
    page_title="NSE NIFTY 50 Analytics Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme styling override
st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .metric-card {
        background-color: #1e222d;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #2a2e39;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# 2. Database Connection Handling
@st.cache_resource
def init_connection():
    raw_url = (
        st.secrets.get("DATABASE_URL")
        if "DATABASE_URL" in st.secrets
        else os.getenv("DATABASE_URL", "")
    )
    raw_url = raw_url.strip().strip("'\"")
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    return create_engine(raw_url)


try:
    engine = init_connection()
except Exception as e:
    st.error(
        f"Failed to connect to cloud database. Verify your DATABASE_URL secret. Error: {e}"
    )
    st.stop()


# Helper function to load cached data
@st.cache_data(ttl=3600)
def run_query(query_str, params=None):
    with engine.connect() as conn:
        return pd.read_sql(text(query_str), conn, params=params)


# 3. Sidebar Controls
st.sidebar.title("📈 Controls & Filters")

# Fetch available tickers
tickers_df = run_query(
    "SELECT ticker, company_name, sector FROM dim_companies ORDER BY ticker;"
)
ticker_list = tickers_df["ticker"].tolist()

selected_ticker = st.sidebar.selectbox(
    "Select Stock Ticker:",
    options=ticker_list,
    index=0 if "RELIANCE.NS" not in ticker_list else ticker_list.index("RELIANCE.NS"),
)

company_info = tickers_df[tickers_df["ticker"] == selected_ticker].iloc[0]
st.sidebar.markdown(f"**Company:** {company_info['company_name']}")
st.sidebar.markdown(f"**Sector:** {company_info['sector']}")

# Date Range Filter
date_bounds = run_query(
    "SELECT MIN(trade_date) as min_date, MAX(trade_date) as max_date FROM fact_stock_prices;"
)
min_db_date = pd.to_datetime(date_bounds["min_date"].iloc[0])
max_db_date = pd.to_datetime(date_bounds["max_date"].iloc[0])

selected_dates = st.sidebar.date_input(
    "Select Date Range:",
    value=(max_db_date - pd.Timedelta(days=365), max_db_date),
    min_value=min_db_date,
    max_value=max_db_date,
)

if len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = min_db_date, max_db_date

# 4. Fetch Analysis Data
stock_sql = """
    SELECT 
        s.trade_date,
        s.open_price,
        s.high_price,
        s.low_price,
        s.close_price,
        s.adj_close,
        s.volume,
        AVG(s.close_price) OVER(PARTITION BY s.ticker ORDER BY s.trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as sma_20,
        AVG(s.close_price) OVER(PARTITION BY s.ticker ORDER BY s.trade_date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) as sma_50,
        AVG(s.close_price) OVER(PARTITION BY s.ticker ORDER BY s.trade_date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) as sma_200
    FROM fact_stock_prices s
    WHERE s.ticker = :ticker AND s.trade_date BETWEEN :start_date AND :end_date
    ORDER BY s.trade_date ASC;
"""

benchmark_sql = """
    SELECT 
        trade_date,
        close_price as index_close
    FROM fact_index_prices
    WHERE index_name = 'NIFTY50' AND trade_date BETWEEN :start_date AND :end_date
    ORDER BY trade_date ASC;
"""

df_stock = run_query(
    stock_sql,
    {
        "ticker": selected_ticker,
        "start_date": start_date,
        "end_date": end_date,
    },
)
df_bench = run_query(
    benchmark_sql, {"start_date": start_date, "end_date": end_date}
)

if df_stock.empty:
    st.warning("No price records found for the selected inputs.")
    st.stop()

# Merge for relative performance calculation
df_merged = pd.merge(df_stock, df_bench, on="trade_date", how="inner")
df_merged["stock_return"] = (
    df_merged["close_price"].pct_change().fillna(0) * 100
)
df_merged["bench_return"] = (
    df_merged["index_close"].pct_change().fillna(0) * 100
)
df_merged["daily_alpha"] = df_merged["stock_return"] - df_merged["bench_return"]

# Normalized performance (Base = 100)
df_merged["stock_norm"] = (
    df_merged["close_price"] / df_merged["close_price"].iloc[0]
) * 100
df_merged["bench_norm"] = (
    df_merged["index_close"] / df_merged["index_close"].iloc[0]
) * 100

# 5. Header & Top KPI Metrics
st.title(f"📊 {company_info['company_name']} ({selected_ticker})")

latest_row = df_merged.iloc[-1]
prev_row = (
    df_merged.iloc[-2] if len(df_merged) > 1 else df_merged.iloc[-1]
)
daily_change = (
    (latest_row["close_price"] - prev_row["close_price"])
    / prev_row["close_price"]
) * 100
cum_stock_return = df_merged["stock_norm"].iloc[-1] - 100
cum_bench_return = df_merged["bench_norm"].iloc[-1] - 100
total_alpha = cum_stock_return - cum_bench_return

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Latest Close",
    f"₹{latest_row['close_price']:,.2f}",
    f"{daily_change:+.2f}%",
)
col2.metric("Period Stock Return", f"{cum_stock_return:+.2f}%")
col3.metric("NIFTY 50 Return", f"{cum_bench_return:+.2f}%")
col4.metric(
    "Net Alpha vs NIFTY",
    f"{total_alpha:+.2f}%",
    delta_color="normal" if total_alpha >= 0 else "inverse",
)

st.markdown("---")

# 6. Interactive Candlestick & Volume Chart
fig_price = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.75, 0.25],
)

# Candlesticks
fig_price.add_trace(
    go.Candlestick(
        x=df_stock["trade_date"],
        open=df_stock["open_price"],
        high=df_stock["high_price"],
        low=df_stock["low_price"],
        close=df_stock["close_price"],
        name="Price",
    ),
    row=1,
    col=1,
)

# SMAs
fig_price.add_trace(
    go.Scatter(
        x=df_stock["trade_date"],
        y=df_stock["sma_20"],
        line=dict(color="#00E676", width=1.5),
        name="SMA 20",
    ),
    row=1,
    col=1,
)
fig_price.add_trace(
    go.Scatter(
        x=df_stock["trade_date"],
        y=df_stock["sma_50"],
        line=dict(color="#FF9100", width=1.5),
        name="SMA 50",
    ),
    row=1,
    col=1,
)
fig_price.add_trace(
    go.Scatter(
        x=df_stock["trade_date"],
        y=df_stock["sma_200"],
        line=dict(color="#2979FF", width=1.5),
        name="SMA 200",
    ),
    row=1,
    col=1,
)

# Volume Bars
colors = [
    "#00E676" if c >= o else "#FF5252"
    for c, o in zip(df_stock["close_price"], df_stock["open_price"])
]
fig_price.add_trace(
    go.Bar(
        x=df_stock["trade_date"],
        y=df_stock["volume"],
        marker_color=colors,
        name="Volume",
    ),
    row=2,
    col=1,
)

fig_price.update_layout(
    template="plotly_dark",
    title="Stock Price Action with Moving Average Overlays",
    yaxis_title="Price (INR)",
    yaxis2_title="Volume",
    xaxis_rangeslider_visible=False,
    height=550,
    margin=dict(l=20, r=20, t=40, b=20),
)

st.plotly_chart(fig_price, use_container_width=True)

# 7. Normalized Relative Performance Chart
st.subheader("⚖️ Relative Performance (Base = 100)")
fig_norm = go.Figure()

fig_norm.add_trace(
    go.Scatter(
        x=df_merged["trade_date"],
        y=df_merged["stock_norm"],
        mode="lines",
        name=selected_ticker,
        line=dict(color="#00E676", width=2),
    )
)
fig_norm.add_trace(
    go.Scatter(
        x=df_merged["trade_date"],
        y=df_merged["bench_norm"],
        mode="lines",
        name="NIFTY 50 Benchmark",
        line=dict(color="#FF9100", width=2, dash="dash"),
    )
)

fig_norm.update_layout(
    template="plotly_dark",
    yaxis_title="Growth Comparison (Normalized to 100)",
    height=400,
    margin=dict(l=20, r=20, t=20, b=20),
)

st.plotly_chart(fig_norm, use_container_width=True)

# 8. Raw SQL Query Data Inspector
with st.expander("🔍 View Raw SQL Data Table"):
    st.dataframe(df_merged, use_container_width=True)