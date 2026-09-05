import sqlite3
import pandas as pd

# Connect to SQLite database (creates 'nse_portfolio.db' if it doesn't exist)
conn = sqlite3.connect("nse_portfolio.db")
cursor = conn.cursor()

print("Creating database schema and tables...")

# 1. Enable Foreign Key Constraints in SQLite
cursor.execute("PRAGMA foreign_keys = ON;")

# 2. Create Dimension Table: dim_companies
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS dim_companies (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector TEXT NOT NULL,
    industry TEXT NOT NULL
);
"""
)

# 3. Create Fact Table: fact_stock_prices
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS fact_stock_prices (
    trade_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    adj_close REAL,
    volume INTEGER,
    PRIMARY KEY (trade_date, ticker),
    FOREIGN KEY (ticker) REFERENCES dim_companies(ticker) ON DELETE CASCADE
);
"""
)

# 4. Create Benchmark Fact Table: fact_index_prices
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS fact_index_prices (
    trade_date TEXT NOT NULL,
    index_name TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    adj_close REAL,
    volume INTEGER,
    PRIMARY KEY (trade_date, index_name)
);
"""
)

# 5. Create Performance Indexes (Crucial for fast SQL Window Functions & JOINs)
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_date ON fact_stock_prices (ticker, trade_date);"
)
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_index_prices_date ON fact_index_prices (trade_date);"
)

conn.commit()

print("Ingesting CSV data into SQLite tables...")

# Read clean CSV files into DataFrames
dim_companies_df = pd.read_csv("dim_companies.csv")
fact_stock_prices_df = pd.read_csv("fact_stock_prices.csv")
fact_index_prices_df = pd.read_csv("fact_index_prices.csv")

# Load DataFrames into SQLite tables
dim_companies_df.to_sql(
    "dim_companies", conn, if_exists="append", index=False
)
fact_stock_prices_df.to_sql(
    "fact_stock_prices", conn, if_exists="append", index=False
)
fact_index_prices_df.to_sql(
    "fact_index_prices", conn, if_exists="append", index=False
)

print("\n--- DATABASE INGESTION VERIFICATION ---")

# Run test query to verify counts
for table in ["dim_companies", "fact_stock_prices", "fact_index_prices"]:
    count = cursor.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0]
    print(f"Table '{table}': {count:,} total records loaded.")

conn.close()
print("\nSUCCESS: Database setup complete! 'nse_portfolio.db' is ready for SQL querying.")