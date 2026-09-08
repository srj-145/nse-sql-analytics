import os
from datetime import datetime, timedelta
import pandas as pd
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
import yfinance as yf

# Create a custom requests session with standard browser headers
session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
)

# 1. Retrieve and sanitize DATABASE_URL
raw_url = os.getenv("DATABASE_URL", "").strip().strip("'\"")

if not raw_url:
    raise ValueError(
        "CRITICAL ERROR: 'DATABASE_URL' secret is missing or empty in GitHub Secrets."
    )

if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

try:
    parsed_url = make_url(raw_url)
    engine = create_engine(parsed_url)
except Exception as e:
    print("URL Parsing Error: Check your DATABASE_URL formatting in GitHub Secrets.")
    raise e


def get_latest_date(table_name):
    with engine.connect() as conn:
        query = text(f"SELECT MAX(trade_date) FROM {table_name};")
        result = conn.execute(query).scalar()
        if result is None:
            return None
        if isinstance(result, str):
            return datetime.strptime(result, "%Y-%m-%d").date()
        if isinstance(result, datetime):
            return result.date()
        return result


try:
    latest_stock_date = get_latest_date("fact_stock_prices")
    latest_index_date = get_latest_date("fact_index_prices")

    start_date = (
        (latest_stock_date + timedelta(days=1))
        if latest_stock_date
        else datetime(2023, 1, 1).date()
    )
    today = datetime.now().date()

    print(f"Latest record in Database: {latest_stock_date}")
    print(f"Checking for new market data from {start_date} to {today}...")

    if start_date >= today:
        print("Database is already up to date. Exiting sync.")
        exit(0)

    # 2. Fetch company tickers using active connection
    with engine.connect() as conn:
        dim_companies = pd.read_sql("SELECT ticker FROM dim_companies;", con=conn)
    tickers = dim_companies["ticker"].tolist()

    # 3. Fetch missing stock price candles
    parsed_stocks = []
    for ticker in tickers:
        df = yf.download(
    ticker,
    start=start_date.strftime("%Y-%m-%d"),
    end=(today + timedelta(days=1)).strftime("%Y-%m-%d"),
    progress=False,
    auto_adjust=False,
    session=session,
)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.reset_index()
            df["ticker"] = ticker
            df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]

            if "adj_close" not in df.columns and "close" in df.columns:
                df["adj_close"] = df["close"]

            df = df.rename(
                columns={
                    "date": "trade_date",
                    "open": "open_price",
                    "high": "high_price",
                    "low": "low_price",
                    "close": "close_price",
                    "volume": "volume",
                }
            )
            parsed_stocks.append(df)

    if parsed_stocks:
        new_stocks_df = pd.concat(parsed_stocks, ignore_index=True)
        new_stocks_df["trade_date"] = pd.to_datetime(
            new_stocks_df["trade_date"]
        ).dt.date
        new_stocks_df = new_stocks_df.dropna(subset=["close_price", "volume"])

        with engine.begin() as conn:
            for idx, row in new_stocks_df.iterrows():
                conn.execute(
                    text(
                        """
                        INSERT INTO fact_stock_prices (trade_date, ticker, open_price, high_price, low_price, close_price, adj_close, volume)
                        VALUES (:trade_date, :ticker, :open_price, :high_price, :low_price, :close_price, :adj_close, :volume)
                        ON CONFLICT (trade_date, ticker) DO NOTHING;
                    """
                    ),
                    row.to_dict(),
                )
        print(f"Successfully inserted {len(new_stocks_df)} new stock price records.")
    else:
        print("No new stock price records found for this date range.")

    # 4. Fetch missing NIFTY 50 benchmark candles
    idx_df = yf.download(
        "^NSEI",
        start=start_date.strftime("%Y-%m-%d"),
        end=(today + timedelta(days=1)).strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=False,
    )

    if not idx_df.empty:
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
                "volume": "volume",
            }
        )
        idx_df["trade_date"] = pd.to_datetime(idx_df["trade_date"]).dt.date
        idx_df["index_name"] = "NIFTY50"

        with engine.begin() as conn:
            for idx, row in idx_df.iterrows():
                conn.execute(
                    text(
                        """
                        INSERT INTO fact_index_prices (trade_date, index_name, open_price, high_price, low_price, close_price, adj_close, volume)
                        VALUES (:trade_date, :index_name, :open_price, :high_price, :low_price, :close_price, :adj_close, :volume)
                        ON CONFLICT (trade_date, index_name) DO NOTHING;
                    """
                    ),
                    row.to_dict(),
                )
        print(f"Successfully inserted {len(idx_df)} new benchmark records.")
    else:
        print("No new benchmark records found for this date range.")

    print("SUCCESS: Incremental daily sync complete.")

except Exception as e:
    print(f"PIPELINE FAILURE: {e}")
    raise e