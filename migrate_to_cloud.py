import os
import pandas as pd
from sqlalchemy import create_engine, text

# Paste your actual Neon PostgreSQL connection string here
DATABASE_URL='postgresql://neondb_owner:npg_JZoATD5kBaW1@ep-dawn-night-aeu5xvlv-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

engine = create_engine(DATABASE_URL)

print("Connecting to cloud PostgreSQL database...")

with engine.connect() as conn:
    # 1. Create Tables
    conn.execute(
        text(
            """
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
    """
        )
    )
    conn.commit()

print("Uploading existing CSV data to Cloud Database...")

dim_companies = pd.read_csv("dim_companies.csv")
fact_stock_prices = pd.read_csv("fact_stock_prices.csv")
fact_index_prices = pd.read_csv("fact_index_prices.csv")

# Load existing CSV data into PostgreSQL
dim_companies.to_sql(
    "dim_companies", engine, if_exists="append", index=False, method="multi"
)
fact_stock_prices.to_sql(
    "fact_stock_prices",
    engine,
    if_exists="append",
    index=False,
    method="multi",
    chunksize=1000,
)
fact_index_prices.to_sql(
    "fact_index_prices", engine, if_exists="append", index=False, method="multi"
)

print("SUCCESS: Cloud database created and initial historical data uploaded!")