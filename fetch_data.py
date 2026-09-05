import pandas as pd
import yfinance as yf

# 1. Define company metadata for the dimension table
companies = [
    {
        "ticker": "HDFCBANK.NS",
        "company_name": "HDFC Bank Ltd",
        "sector": "Banking & Financials",
        "industry": "Private Bank",
    },
    {
        "ticker": "ICICIBANK.NS",
        "company_name": "ICICI Bank Ltd",
        "sector": "Banking & Financials",
        "industry": "Private Bank",
    },
    {
        "ticker": "SBIN.NS",
        "company_name": "State Bank of India",
        "sector": "Banking & Financials",
        "industry": "Public Bank",
    },
    {
        "ticker": "TCS.NS",
        "company_name": "Tata Consultancy Services Ltd",
        "sector": "Information Technology",
        "industry": "IT Services",
    },
    {
        "ticker": "INFY.NS",
        "company_name": "Infosys Ltd",
        "sector": "Information Technology",
        "industry": "IT Services",
    },
    {
        "ticker": "WIPRO.NS",
        "company_name": "Wipro Ltd",
        "sector": "Information Technology",
        "industry": "IT Services",
    },
    {
        "ticker": "RELIANCE.NS",
        "company_name": "Reliance Industries Ltd",
        "sector": "Energy & Industrials",
        "industry": "Conglomerate",
    },
    {
        "ticker": "LT.NS",
        "company_name": "Larsen & Toubro Ltd",
        "sector": "Energy & Industrials",
        "industry": "Engineering",
    },
    {
        "ticker": "NTPC.NS",
        "company_name": "NTPC Ltd",
        "sector": "Energy & Industrials",
        "industry": "Power Generation",
    },
    {
        "ticker": "HINDUNILVR.NS",
        "company_name": "Hindustan Unilever Ltd",
        "sector": "FMCG & Consumer",
        "industry": "Consumer Goods",
    },
    {
        "ticker": "ITC.NS",
        "company_name": "ITC Ltd",
        "sector": "FMCG & Consumer",
        "industry": "Consumer Goods",
    },
    {
        "ticker": "TITAN.NS",
        "company_name": "Titan Company Ltd",
        "sector": "FMCG & Consumer",
        "industry": "Consumer Durables",
    },
]

dim_companies = pd.DataFrame(companies)
tickers = dim_companies["ticker"].tolist()

print("Fetching stock price data from Yahoo Finance...")

parsed_stocks = []
for ticker in tickers:
    df = yf.download(
        ticker,
        start="2023-01-01",
        end="2026-08-31",
        progress=False,
        auto_adjust=False,
    )

    # Flatten multi-index columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    df["ticker"] = ticker

    # Standardize column names to lowercase with underscores
    df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]

    # Handle cases where adj_close isn't returned separately
    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]

    df = df.rename(columns={"date": "trade_date"})
    parsed_stocks.append(df)

fact_stock_prices = pd.concat(parsed_stocks, ignore_index=True)

# Standardize date format
fact_stock_prices["trade_date"] = pd.to_datetime(
    fact_stock_prices["trade_date"]
).dt.date

# Rename metric columns to matching schema names
column_mapping = {
    "open": "open_price",
    "high": "high_price",
    "low": "low_price",
    "close": "close_price",
    "adj_close": "adj_close",
    "volume": "volume",
}
fact_stock_prices = fact_stock_prices.rename(columns=column_mapping)

# Remove empty rows and filter target columns
fact_stock_prices = fact_stock_prices.dropna(subset=["close_price", "volume"])
target_columns = [
    "trade_date",
    "ticker",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "adj_close",
    "volume",
]
fact_stock_prices = fact_stock_prices[target_columns]

print("Fetching NIFTY 50 benchmark data...")

idx_df = yf.download(
    "^NSEI",
    start="2023-01-01",
    end="2026-08-31",
    progress=False,
    auto_adjust=False,
)
if isinstance(idx_df.columns, pd.MultiIndex):
    idx_df.columns = idx_df.columns.get_level_values(0)

idx_df = idx_df.reset_index()
idx_df.columns = [str(col).lower().replace(" ", "_") for col in idx_df.columns]

if "adj_close" not in idx_df.columns and "close" in idx_df.columns:
    idx_df["adj_close"] = idx_df["close"]

idx_df = idx_df.rename(
    columns={
        "date": "trade_date",
        "open": "open_price",
        "high": "high_price",
        "low": "low_price",
        "close": "close_price",
        "adj_close": "adj_close",
        "volume": "volume",
    }
)

idx_df["trade_date"] = pd.to_datetime(idx_df["trade_date"]).dt.date
idx_df["index_name"] = "NIFTY50"

fact_index_prices = idx_df[
    [
        "trade_date",
        "index_name",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "adj_close",
        "volume",
    ]
]

# Export clean CSVs
dim_companies.to_csv("dim_companies.csv", index=False)
fact_stock_prices.to_csv("fact_stock_prices.csv", index=False)
fact_index_prices.to_csv("fact_index_prices.csv", index=False)

print("SUCCESS: All 3 CSV files generated successfully!")