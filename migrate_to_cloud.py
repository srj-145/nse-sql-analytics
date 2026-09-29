import os
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Fetch Database Connection URL
raw_url = os.getenv("DATABASE_URL", "")

if not raw_url:
    raise ValueError(
        "DATABASE_URL environment variable is not set. Run: export DATABASE_URL='...'"
    )

# Fix legacy postgres:// protocol prefix for SQLAlchemy
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(raw_url)

print("Connecting to cloud PostgreSQL database...")

# 2. Schema Creation and Migration
with engine.begin() as conn:
    print("Creating tables if they do not exist...")
    
    conn.execute(
        text("""
        CREATE TABLE IF NOT EXISTS dim_companies (
            ticker VARCHAR(20) PRIMARY KEY,
            company_name VARCHAR(100) NOT NULL,
            sector VARCHAR(50) NOT NULL,
            industry VARCHAR(50) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fact_stock_prices (
            trade_date DATE NOT NULL,
            ticker VARCHAR(20) NOT NULL REFERENCES dim_companies(ticker) ON DELETE CASCADE,
            open_price NUMERIC(10, 2),
            high_price NUMERIC(10, 2),
            low_price NUMERIC(10, 2),
            close_price NUMERIC(10, 2),
            adj_close NUMERIC(10, 2),
            volume BIGINT,
            PRIMARY KEY (trade_date, ticker)
        );

        CREATE TABLE IF NOT EXISTS fact_index_prices (
            trade_date DATE NOT NULL,
            index_name VARCHAR(20) NOT NULL,
            open_price NUMERIC(10, 2),
            high_price NUMERIC(10, 2),
            low_price NUMERIC(10, 2),
            close_price NUMERIC(10, 2),
            adj_close NUMERIC(10, 2),
            volume BIGINT,
            PRIMARY KEY (trade_date, index_name)
        );

        CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_date ON fact_stock_prices (ticker, trade_date);
        CREATE INDEX IF NOT EXISTS idx_index_prices_date ON fact_index_prices (trade_date);
        """)
    )

# 3. Seed CSV Data into Cloud PostgreSQL
if os.path.exists("dim_companies.csv"):
    print("Migrating dim_companies.csv...")
    df_comp = pd.read_csv("dim_companies.csv")
    df_comp.to_sql("dim_companies", engine, if_exists="append", index=False)

if os.path.exists("fact_stock_prices.csv"):
    print("Migrating fact_stock_prices.csv...")
    df_stocks = pd.read_csv("fact_stock_prices.csv")
    df_stocks.to_sql("fact_stock_prices", engine, if_exists="append", index=False)

if os.path.exists("fact_index_prices.csv"):
    print("Migrating fact_index_prices.csv...")
    df_index = pd.read_csv("fact_index_prices.csv")
    df_index.to_sql("fact_index_prices", engine, if_exists="append", index=False)

print("Migration completed successfully!")