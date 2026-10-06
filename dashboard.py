import os
import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

st.set_page_config(page_title="NSE NIFTY 50 Analytics", layout="wide")

TOP_25_COMPANIES = [
    {"ticker": "ADANIENT.NS", "company_name": "Adani Enterprises Ltd", "sector": "Metals & Mining"},
    {"ticker": "AXISBANK.NS", "company_name": "Axis Bank Ltd", "sector": "Financial Services"},
    {"ticker": "BAJFINANCE.NS", "company_name": "Bajaj Finance Ltd", "sector": "Financial Services"},
    {"ticker": "BHARTIARTL.NS", "company_name": "Bharti Airtel Ltd", "sector": "Telecommunication"},
    {"ticker": "HDFCBANK.NS", "company_name": "HDFC Bank Ltd", "sector": "Financial Services"},
    {"ticker": "HINDUNILVR.NS", "company_name": "Hindustan Unilever Ltd", "sector": "Consumer Goods"},
    {"ticker": "ICICIBANK.NS", "company_name": "ICICI Bank Ltd", "sector": "Financial Services"},
    {"ticker": "INFY.NS", "company_name": "Infosys Ltd", "sector": "Information Technology"},
    {"ticker": "ITC.NS", "company_name": "ITC Ltd", "sector": "Consumer Goods"},
    {"ticker": "KOTAKBANK.NS", "company_name": "Kotak Mahindra Bank Ltd", "sector": "Financial Services"},
    {"ticker": "LT.NS", "company_name": "Larsen & Toubro Ltd", "sector": "Construction & Engineering"},
    {"ticker": "LTIM.NS", "company_name": "LTIMindtree Ltd", "sector": "Information Technology"},
    {"ticker": "M&M.NS", "company_name": "Mahindra & Mahindra Ltd", "sector": "Automobile"},
    {"ticker": "MARUTI.NS", "company_name": "Maruti Suzuki India Ltd", "sector": "Automobile"},
    {"ticker": "NTPC.NS", "company_name": "NTPC Ltd", "sector": "Power & Energy"},
    {"ticker": "ONGC.NS", "company_name": "Oil & Natural Gas Corporation Ltd", "sector": "Energy"},
    {"ticker": "POWERGRID.NS", "company_name": "Power Grid Corporation of India Ltd", "sector": "Power & Energy"},
    {"ticker": "RELIANCE.NS", "company_name": "Reliance Industries Ltd", "sector": "Energy & Industrials"},
    {"ticker": "SBIN.NS", "company_name": "State Bank of India", "sector": "Financial Services"},
    {"ticker": "SUNPHARMA.NS", "company_name": "Sun Pharmaceutical Industries Ltd", "sector": "Healthcare & Pharma"},
    {"ticker": "TATAMOTORS.NS", "company_name": "Tata Motors Ltd", "sector": "Automobile"},
    {"ticker": "TCS.NS", "company_name": "Tata Consultancy Services Ltd", "sector": "Information Technology"},
    {"ticker": "TITAN.NS", "company_name": "Titan Company Ltd", "sector": "Consumer Goods"},
    {"ticker": "ULTRACEMCO.NS", "company_name": "UltraTech Cement Ltd", "sector": "Construction Materials"},
    {"ticker": "WIPRO.NS", "company_name": "Wipro Ltd", "sector": "Information Technology"}
]

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

def ensure_companies_seeded():
    seed_sql = text("""
        INSERT INTO dim_companies (ticker, company_name, sector)
        SELECT :ticker, :company_name, :sector
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_companies WHERE ticker = :ticker
        );
    """)
    update_sql = text("""
        UPDATE dim_companies
        SET company_name = :company_name, sector = :sector
        WHERE ticker = :ticker;
    """)
    try:
        with engine.begin() as conn:
            for comp in TOP_25_COMPANIES:
                res = conn.execute(seed_sql, comp)
                if res.rowcount == 0:
                    conn.execute(update_sql, comp)
    except Exception as e:
        st.sidebar.error(f"Error seeding database: {e}")

@st.cache_data(ttl=10)
def load_companies():
    ensure_companies_seeded()
    query = "SELECT ticker, company_name, sector FROM dim_companies ORDER BY company_name LIMIT 25;"
    return pd.read_sql(query, engine)

@st.cache_data(ttl=10)
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

@st.cache_data(ttl=60)
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

@st.cache_data(ttl=60)
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

ticker_to_name = dict(zip(companies_df['ticker'], companies_df['company_name']))

selected_ticker = st.sidebar.selectbox(
    f"Select Stock Ticker ({len(companies_df)} Available):",
    options=companies_df['ticker'].tolist(),
    format_func=lambda x: f"{ticker_to_name.get(x, x)} ({x})"
)

company_info = companies_df[companies_df['ticker'] == selected_ticker].iloc[0]
st.sidebar.write(f"**Company:** {company_info['company_name']}")
st.sidebar.write(f"**Sector:** {company_info['sector']}")

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
    st.warning("No price data available in the database for this ticker yet. Run the GitHub Action sync workflow to fetch historical price data.")
else:
    stock_df['SMA_20'] = stock_df['close_price'].rolling(window=20).mean()
    stock_df['SMA_50'] = stock_df['close_price'].rolling(window=50).mean()

    st.subheader(f"{company_info['company_name']} ({selected_ticker}) - Price Action")

    latest_close = stock_df['close_price'].iloc[-1]
    prev_close = stock_df['close_price'].iloc[-2] if len(stock_df) > 1 else latest_close
    chg = latest_close - prev_close
    pct_chg = (chg / prev_close) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Close", f"₹{latest_close:,.2f}", f"{chg:+,.2f} ({pct_chg:+.2f}%)")
    col2.metric("Period High", f"₹{stock_df['high_price'].max():,.2f}")
    col3.metric("Period Low", f"₹{stock_df['low_price'].min():,.2f}")

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
