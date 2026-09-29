# NSE / NIFTY 50 Market Data & Analytics Engine

> An end-to-end Python + SQL financial analytics project for collecting NSE market data, building a relational data model, running analytical SQL, maintaining an incremental cloud pipeline, and visualizing stock performance against the NIFTY 50.

## Project Overview

This project was built to explore how a market-data workflow can be designed from data ingestion all the way to an interactive analytics interface.

The system collects historical price data for a selected set of NSE-listed companies and the NIFTY 50 benchmark through Yahoo Finance. The data is cleaned and organized into dimension/fact tables, loaded into a relational database, analyzed with SQL window functions, and presented through a Streamlit dashboard.

The project covers the complete flow:

```text
Market Data
    ↓
Yahoo Finance / yfinance
    ↓
Python Data Preparation
    ↓
CSV Data Layer
    ↓
Relational Database
    ↓
SQL Analytics
    ↓
Incremental Cloud Updates
    ↓
Streamlit + Plotly Dashboard
```

## What the Project Demonstrates

This repository combines several practical data and software concepts:

- **Python data ingestion** with `pandas` and `yfinance`
- **Relational data modeling** using dimension and fact tables
- **SQL analytics** using window functions
- **Financial metrics** such as daily returns, moving averages, relative performance, and alpha
- **ETL/data engineering** from raw market data to structured analytical data
- **Incremental data synchronization** rather than repeatedly downloading the entire dataset
- **PostgreSQL cloud storage** through Neon
- **Interactive data visualization** using Streamlit and Plotly
- **Local SQL development** with SQLite
- **Database performance optimization** through indexes and composite keys

---

## Dashboard

The Streamlit dashboard allows a user to select a stock and a date range and then inspect its performance.

### Key dashboard features

**1. Stock and company selection**

Users can select from the companies stored in `dim_companies`.

**2. Date-range analysis**

The dashboard dynamically determines the available market-data range and allows users to select the period they want to analyze.

**3. KPI summary**

The dashboard calculates and displays:

- Latest close
- Daily price change
- Selected-period stock return
- Selected-period NIFTY 50 return
- Net alpha versus NIFTY 50

**4. Technical price chart**

An interactive Plotly chart combines:

- Candlestick price action
- 20-day Simple Moving Average
- 50-day Simple Moving Average
- 200-day Simple Moving Average
- Trading volume

**5. Relative performance**

The selected stock and NIFTY 50 are both normalized to 100 at the beginning of the selected period.

This allows their relative performance to be compared directly.

---

## Data Coverage

The initial data collection script downloads historical data beginning on:

```text
2023-01-01
```

and uses:

```text
2026-08-31
```

as the initial end date.

The benchmark is the NIFTY 50 Yahoo Finance symbol:

```text
^NSEI
```

The project currently tracks a small representative set of NSE companies across several sectors, including banking & financials, information technology, energy & industrials, and FMCG/consumer companies.

The company metadata is stored separately from price observations, allowing the database to support joins and sector-level analysis.

---

## Database Architecture

The project uses a simple star-schema-inspired model.

### `dim_companies`

Stores descriptive company information:

```text
ticker
company_name
sector
industry
```

### `fact_stock_prices`

Stores daily OHLCV observations for individual stocks:

```text
trade_date
ticker
open_price
high_price
low_price
close_price
adj_close
volume
```

The primary key is:

```text
(trade_date, ticker)
```

### `fact_index_prices`

Stores daily NIFTY 50 benchmark observations:

```text
trade_date
index_name
open_price
high_price
low_price
close_price
adj_close
volume
```

The primary key is:

```text
(trade_date, index_name)
```

Indexes are created on ticker/date and index/date combinations to support time-series queries efficiently.

---

## SQL Analytics

One of the main goals of the project is to demonstrate analytical SQL rather than relying entirely on Python calculations.

### Daily returns

`LAG()` is used to retrieve the previous trading day's closing price:

```sql
LAG(close_price)
OVER (PARTITION BY ticker ORDER BY trade_date)
```

This is then used to calculate daily percentage returns.

### Monthly performance ranking

The project uses:

- `FIRST_VALUE()`
- `LAST_VALUE()`
- `RANK()`

to determine monthly performance and rank stocks by return.

### Moving averages

Windowed `AVG()` calculations are used to derive moving averages.

The dashboard uses:

- 20-day SMA
- 50-day SMA
- 200-day SMA

### Alpha against NIFTY 50

The project compares stock and benchmark daily returns:

```text
Alpha = Stock Return - NIFTY 50 Return
```

This provides a simple measure of whether the selected stock outperformed or underperformed the benchmark during a trading session.

---

## Incremental Data Pipeline

A major part of the project is the daily update mechanism.

Instead of downloading the entire historical dataset every time, `update_daily_data.py` first checks the latest date already present in the database.

```text
Database
   │
   ├── Find MAX(trade_date)
   │
   ▼
Determine next required date
   │
   ▼
Download only missing data
   │
   ▼
Insert new records
   │
   ▼
Ignore duplicates
```

New rows are inserted using PostgreSQL conflict handling:

```sql
ON CONFLICT (trade_date, ticker) DO NOTHING
```

and the equivalent conflict logic is used for NIFTY 50 benchmark records.

This makes the update process repeatable and prevents duplicate observations.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python |
| Data processing | pandas |
| Market data | yfinance / Yahoo Finance |
| Local database | SQLite |
| Cloud database | PostgreSQL / Neon |
| Database interface | SQLAlchemy |
| PostgreSQL driver | psycopg2 |
| SQL analytics | SQL window functions |
| Visualization | Plotly |
| Dashboard | Streamlit |
| Automation | GitHub Actions |
| License | MIT |

The dependency versions are maintained in `requirements.txt`.

---

## Repository Structure

```text
.
├── dashboard.py
├── fetch_data.py
├── ingest_db.py
├── migrate_to_cloud.py
├── update_daily_data.py
├── run_queries.py
├── requirements.txt
├── LICENSE
├── dim_companies.csv
├── fact_stock_prices.csv
├── fact_index_prices.csv
└── nse_portfolio.db
```

### Main files

| File | Purpose |
|---|---|
| `fetch_data.py` | Downloads and prepares the initial historical market dataset |
| `ingest_db.py` | Creates the local SQLite schema and loads CSV data |
| `run_queries.py` | Demonstrates analytical SQL queries |
| `migrate_to_cloud.py` | Creates/populates the PostgreSQL cloud database |
| `update_daily_data.py` | Performs incremental market-data synchronization |
| `dashboard.py` | Runs the Streamlit analytics dashboard |
| `requirements.txt` | Python dependencies |
| `LICENSE` | MIT license |

---

## Running the Project Locally

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_REPOSITORY_NAME>
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Generate market-data CSVs

```bash
python fetch_data.py
```

### 5. Build the local SQLite database

```bash
python ingest_db.py
```

### 6. Run the SQL analytics examples

```bash
python run_queries.py
```

### 7. Configure PostgreSQL

Set:

```text
DATABASE_URL=<your PostgreSQL connection string>
```

Then run:

```bash
python migrate_to_cloud.py
```

### 8. Launch the dashboard

```bash
streamlit run dashboard.py
```

---

## Security

**Do not commit database credentials to GitHub.**

The development copy of `migrate_to_cloud.py` contains a PostgreSQL connection string. Before publishing this repository, replace any hard-coded credential with an environment variable or secret.

For example:

```python
DATABASE_URL = os.getenv("DATABASE_URL")
```

If a real credential has already been pushed to a repository or otherwise exposed, rotate/revoke it before publishing the project.

For deployed Streamlit applications, store the connection string in Streamlit secrets rather than in source code.

---

## Data Source

Market data is retrieved through `yfinance`, which provides access to Yahoo Finance market data.

This project is intended for **educational and analytical purposes**. It is not a trading system and does not provide investment advice.

---

## Why This Project?

The project was designed as a compact end-to-end demonstration of how financial market data can move through a modern analytics workflow:

```text
Collect
  ↓
Clean
  ↓
Model
  ↓
Store
  ↓
Query
  ↓
Analyze
  ↓
Visualize
  ↓
Automate
```

Rather than treating SQL, Python, databases, and dashboards as separate exercises, the project connects them into one working pipeline.

---

## Future Improvements

Potential extensions include:

- Expanding coverage to all NIFTY 50 constituents
- Adding sector-level dashboards
- Adding additional technical indicators
- Adding volatility and risk metrics
- Adding portfolio-level analytics
- Adding automated data-quality checks
- Adding more robust retry/error handling for external data requests
- Adding automated tests
- Adding GitHub Actions workflow configuration
- Adding authentication/access controls for a deployed dashboard

---

## License

This project is released under the **MIT License**. See [`LICENSE`](LICENSE) for details.
