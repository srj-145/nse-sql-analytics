# NSE / NIFTY 50 Analytics — Code Documentation

## Overview

This repository contains a Python + SQL data pipeline for collecting NSE stock-market data, storing it in a relational database, running analytical SQL queries, and serving the results through an interactive Streamlit dashboard.

The project works with:

- NSE-listed equities
- NIFTY 50 benchmark data
- OHLCV market data
- Company, sector, and industry metadata
- SQL window functions for financial analytics
- SQLite for local development/querying
- PostgreSQL/Neon for cloud storage
- Streamlit + Plotly for visualization

The initial historical dataset covers the period beginning **2023-01-01** and is generated through Yahoo Finance using `yfinance`.

---

## Project Workflow

```text
Yahoo Finance
     │
     ▼
fetch_data.py
     │
     ├── dim_companies.csv
     ├── fact_stock_prices.csv
     └── fact_index_prices.csv
     │
     ▼
ingest_db.py
     │
     ▼
nse_portfolio.db (SQLite)
     │
     ├── run_queries.py
     │
     └── migrate_to_cloud.py
              │
              ▼
       Neon PostgreSQL
              │
              ├── update_daily_data.py
              │
              └── dashboard.py
                       │
                       ▼
                Streamlit Dashboard
```

---

## File-by-File Documentation

### `fetch_data.py`

Responsible for creating the initial historical dataset.

It:

1. Defines company metadata for the tracked NSE companies.
2. Downloads historical stock data using `yfinance`.
3. Downloads NIFTY 50 data using the Yahoo Finance symbol `^NSEI`.
4. Standardizes column names and dates.
5. Removes incomplete stock records.
6. Produces three CSV files:
   - `dim_companies.csv`
   - `fact_stock_prices.csv`
   - `fact_index_prices.csv`

The tracked company set includes banking, IT, energy/industrials, FMCG/consumer, and other represented sectors.

Example Yahoo Finance symbols include:

```text
HDFCBANK.NS
ICICIBANK.NS
SBIN.NS
TCS.NS
INFY.NS
WIPRO.NS
RELIANCE.NS
LT.NS
NTPC.NS
HINDUNILVR.NS
ITC.NS
TITAN.NS
```

### `ingest_db.py`

Creates the local SQLite database and loads the generated CSV files.

Database:

```text
nse_portfolio.db
```

Tables:

- `dim_companies`
- `fact_stock_prices`
- `fact_index_prices`

It also creates indexes on ticker/date and index/date to improve query performance.

### `run_queries.py`

Demonstrates analytical SQL against the local SQLite database.

The script contains four examples:

#### 1. Daily Returns — `LAG()`

Calculates the previous closing price and daily percentage return for each stock.

```sql
LAG(close_price, 1)
OVER (PARTITION BY ticker ORDER BY trade_date)
```

#### 2. Monthly Performance Ranking — `RANK()`

Calculates monthly returns and ranks stocks by performance within each month.

It uses `FIRST_VALUE()` and `LAST_VALUE()` to identify monthly starting and ending prices.

#### 3. 30-Day SMA and Volatility Spread

Calculates:

- 30-day moving average
- 30-day high-low price spread

using SQL window functions.

#### 4. Alpha vs NIFTY 50

Compares a stock's daily return with the NIFTY 50 daily return and calculates:

```text
Alpha = Stock Return - NIFTY 50 Return
```

The example query uses `TCS.NS`.

---

## Database Schema

### `dim_companies`

Dimension table containing company metadata.

| Column | Description |
|---|---|
| `ticker` | NSE/Yahoo Finance ticker |
| `company_name` | Company name |
| `sector` | Sector classification |
| `industry` | Industry classification |

`ticker` is the primary key.

### `fact_stock_prices`

Fact table containing historical stock price data.

| Column | Description |
|---|---|
| `trade_date` | Trading date |
| `ticker` | Stock ticker |
| `open_price` | Opening price |
| `high_price` | Intraday high |
| `low_price` | Intraday low |
| `close_price` | Closing price |
| `adj_close` | Adjusted closing price |
| `volume` | Trading volume |

The composite key is:

```text
(trade_date, ticker)
```

### `fact_index_prices`

Fact table containing benchmark/index data.

| Column | Description |
|---|---|
| `trade_date` | Trading date |
| `index_name` | Benchmark name |
| `open_price` | Opening value |
| `high_price` | Intraday high |
| `low_price` | Intraday low |
| `close_price` | Closing value |
| `adj_close` | Adjusted closing value |
| `volume` | Available volume field |

The composite key is:

```text
(trade_date, index_name)
```

---

## `migrate_to_cloud.py`

Moves the historical dataset from CSV files into a PostgreSQL database.

The script:

1. Connects to PostgreSQL.
2. Creates the three project tables if they do not exist.
3. Creates supporting indexes.
4. Reads the three CSV datasets.
5. Uploads the historical records.

The intended cloud database is a PostgreSQL instance hosted by Neon.

### Important Security Note

Never commit a real PostgreSQL connection string, password, API key, or other credential to GitHub.

The current development version of `migrate_to_cloud.py` contains a database credential directly in the source file. Before publishing this repository, remove that credential and rotate/revoke it if it has ever been exposed.

Use an environment variable instead:

```python
DATABASE_URL = os.getenv("DATABASE_URL")
```

---

## `update_daily_data.py`

Provides incremental daily synchronization for the cloud database.

Its main logic is:

1. Read `DATABASE_URL`.
2. Connect to PostgreSQL.
3. Find the latest date already stored.
4. Calculate the next date that needs to be downloaded.
5. Read the tracked tickers from `dim_companies`.
6. Download missing stock data.
7. Download missing NIFTY 50 data.
8. Insert new rows.
9. Ignore records that already exist using `ON CONFLICT DO NOTHING`.

This makes the pipeline incremental instead of downloading the complete historical dataset every day.

---

## `dashboard.py`

Runs the Streamlit analytics dashboard.

It connects to the PostgreSQL database using `DATABASE_URL` from Streamlit secrets or the environment.

The dashboard provides:

### Stock Selection

Users can select a tracked ticker and see its company and sector information.

### Date Filtering

Users can select a date range within the available database history.

### KPI Metrics

The dashboard displays:

- Latest closing price
- Daily percentage change
- Stock return over the selected period
- NIFTY 50 return over the selected period
- Net alpha versus NIFTY 50

### Candlestick Chart

The primary chart contains:

- OHLC candlesticks
- 20-day SMA
- 50-day SMA
- 200-day SMA
- Trading volume

### Relative Performance

Both the selected stock and NIFTY 50 are normalized to a starting value of 100.

This makes it easier to compare percentage growth over the selected period.

### SQL Data Inspector

An expandable table exposes the merged stock/benchmark dataset used by the dashboard.

---

## Moving Average Calculations

The dashboard calculates SMAs using SQL window functions.

### SMA 20

```sql
AVG(close_price) OVER (
    PARTITION BY ticker
    ORDER BY trade_date
    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
)
```

The same approach is used for:

- SMA 50
- SMA 200

This keeps the analytical calculation close to the database layer.

---

## Relative Performance and Alpha

For every matching trading date:

```text
Stock Daily Return = % change in stock close
NIFTY Daily Return  = % change in NIFTY 50 close

Daily Alpha = Stock Daily Return - NIFTY Daily Return
```

The dashboard also normalizes both series:

```text
Normalized Stock = Stock Close / First Stock Close × 100
Normalized NIFTY = NIFTY Close / First NIFTY Close × 100
```

The resulting chart starts both series at 100 and shows their relative growth.

---

## Dependencies

The project uses:

- Python
- pandas
- yfinance
- SQLAlchemy
- psycopg2-binary
- requests
- Streamlit
- Plotly

Install them with:

```bash
pip install -r requirements.txt
```

---

## Local Setup

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_REPOSITORY_NAME>
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**macOS/Linux**

```bash
source .venv/bin/activate
```

**Windows**

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Generate the historical datasets

```bash
python fetch_data.py
```

This generates:

```text
dim_companies.csv
fact_stock_prices.csv
fact_index_prices.csv
```

### 5. Create the local SQLite database

```bash
python ingest_db.py
```

This creates:

```text
nse_portfolio.db
```

### 6. Run the analytical SQL examples

```bash
python run_queries.py
```

### 7. Configure PostgreSQL

Set your PostgreSQL connection string as an environment variable:

```bash
export DATABASE_URL="your-postgresql-connection-string"
```

Then run:

```bash
python migrate_to_cloud.py
```

### 8. Run the dashboard

```bash
streamlit run dashboard.py
```

---

## Environment Variables

The project expects:

```text
DATABASE_URL
```

For local development, it can be stored in a `.env` file if your environment is configured to load it.

For Streamlit deployment, configure it as a Streamlit secret.

For GitHub Actions, configure it as a repository secret.

Do not commit credentials to the repository.

---

## Data Model

The project follows a simple star-schema-inspired structure:

```text
              dim_companies
                    │
                    │ ticker
                    ▼
          fact_stock_prices
                    │
                    │ trade_date
                    │
                    ▼
          fact_index_prices
```

`dim_companies` provides descriptive attributes, while the fact tables contain market observations.

---

## Purpose of the Codebase

The code demonstrates an end-to-end analytics workflow rather than only a dashboard:

```text
Data Collection
      ↓
Data Cleaning
      ↓
Data Modeling
      ↓
Database Ingestion
      ↓
SQL Analytics
      ↓
Incremental Updates
      ↓
Cloud Database
      ↓
Interactive Visualization
```

This makes the project useful as a practical demonstration of Python, SQL, relational data modeling, ETL/data engineering, financial analytics, and dashboard development.
