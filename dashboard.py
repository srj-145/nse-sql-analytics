import os
import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

st.set_page_config(page_title="NSE NIFTY 50 Analytics", layout="wide")

@st.cache_resource
def get_db_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        st.error("DATABASE_URL environment variable is not set.")
        st.stop()
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return create_engine(db_url)

engine = get_db_engine()

@st.cache_data(ttl=3600)
def load_companies():
    query = "SELECT ticker, company_name, sector FROM dim_companies ORDER BY company_name;"
    return pd.read_sql(query, engine)

# Low cache TTL ensures fresh database bounds are fetched promptly
@st.cache_data(ttl=60)
def get_date_bounds():
    with engine.connect() as conn:
        min_date = conn.execute(text("SELECT MIN(trade_date) FROM fact_stock_prices;")).scalar()
        max_date = conn.execute(text("SELECT MAX(trade_date) FROM fact_stock_prices;")).scalar()
    today = datetime.date.today()
    if min_date is None:
        min_date = datetime.date(2024, 1, 1)
    if max_date is None:
        max_date = today
    return min_date, max_date

@st.cache_data(ttl=300)
def load_stock_data(ticker, start_date, end_date):
    query = text("""
        SELECT trade_date, open_price, high_price, low_price, close_price, adj_close, volume
        FROM fact_stock_prices
        WHERE ticker = :ticker AND trade_date BETWEEN :start_date AND :end_date
        ORDER BY trade_date ASC;
    """)
    df = pd.read_sql(query, engine, params={"ticker": ticker, "start_date": start_date, "end_date": end_date})
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df

@st.cache_data(ttl=300)
def load_index_data(start_date, end_date):
    query = text("""
        SELECT trade_date, close_price
        FROM fact_index_prices
        WHERE index_name = 'NIFTY 50' AND trade_date BETWEEN :start_date AND :end_date
        ORDER BY trade_date ASC;
    """)
    df = pd.read_sql(query, engine, params={"start_date": start_date, "end_date": end_date})
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    return df

st.title("📈 NSE NIFTY 50 Market Data Engine & Analytics")

companies_df = load_companies()
min_db_date, max_db_date = get_date_bounds()
today_date = datetime.date.today()

st.sidebar.header("Controls & Filters")

selected_ticker = st.sidebar.selectbox(
    "Select Stock Ticker:",
    options=companies_df['ticker'].tolist()
)

company_info = companies_df[companies_df['ticker'] == selected_ticker].iloc[0]
st.sidebar.write(f"**Company:** {company_info['company_name']}")
st.sidebar.write(f"**Sector:** {company_info['sector']}")

# Calendar UI allows selection up to current date
date_range = st.sidebar.date_input(
    "Select Date Range:",
    value=(min_db_date, max_db_date),
    min_value=min_db_date,
    max_value=today_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_db_date, max_db_date

stock_df = load_stock_data(selected_ticker, start_date, end_date)
index_df = load_index_data(start_date, end_date)

if stock_df.empty:
    st.warning("No data available for the selected date range in the database.")
else:
    # Technical Indicators
    stock_df['SMA_20'] = stock_df['close_price'].rolling(window=20).mean()
    stock_df['SMA_50'] = stock_df['close_price'].rolling(window=50).mean()

    st.subheader(f"{company_info['company_name']} ({selected_ticker}) - Price Action")

    # Metrics
    latest_close = stock_df['close_price'].iloc[-1]
    prev_close = stock_df['close_price'].iloc[-2] if len(stock_df) > 1 else latest_close
    chg = latest_close - prev_close
    pct_chg = (chg / prev_close) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Close", f"₹{latest_close:,.2f}", f"{chg:+,.2f} ({pct_chg:+.2f}%)")
    col2.metric("Period High", f"₹{stock_df['high_price'].max():,.2f}")
    col3.metric("Period Low", f"₹{stock_df['low_price'].min():,.2f}")

    # Candlestick Chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=stock_df['trade_date'],
        open=stock_df['open_price'],
        high=stock_df['high_price'],
        low=stock_df['low_price'],
        close=stock_df['close_price'],
        name="OHLC"
    ))
    fig.add_trace(go.Scatter(x=stock_df['trade_date'], y=stock_df['SMA_20'], name="SMA 20", line=dict(color="orange", width=1)))
    fig.add_trace(go.Scatter(x=stock_df['trade_date'], y=stock_df['SMA_50'], name="SMA 50", line=dict(color="blue", width=1)))

    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Relative Performance Comparison
    st.subheader("Relative Performance vs NIFTY 50")
    if not index_df.empty:
        merged = pd.merge(stock_df, index_df, on="trade_date", suffixes=('_stock', '_index'))
        if not merged.empty:
            merged['Stock_Norm'] = (merged['close_price_stock'] / merged['close_price_stock'].iloc[0]) * 100
            merged['Index_Norm'] = (merged['close_price_index'] / merged['close_price_index'].iloc[0]) * 100

            fig_rel = go.Figure()
            fig_rel.add_trace(go.Scatter(x=merged['trade_date'], y=merged['Stock_Norm'], name=selected_ticker, line=dict(color="green", width=2)))
            fig_rel.add_trace(go.Scatter(x=merged['trade_date'], y=merged['Index_Norm'], name="NIFTY 50", line=dict(color="gray", width=2, dash="dash")))
            fig_rel.update_layout(template="plotly_dark", height=400, yaxis_title="Normalized Return (Base = 100)")
            st.plotly_chart(fig_rel, use_container_width=True)
