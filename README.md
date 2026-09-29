# 📈 NSE NIFTY 50 Market Data Engine & Analytics Dashboard

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://nse-sql-analytics-140423102005.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon.tech-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated%20ETL-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/features/actions)

A fully automated, zero-cost financial analytics platform that ingests, stores, and visualizes daily price action and technical performance metrics for NIFTY 50 stocks against benchmark indices.

---

## 🚀 Live Application

🔗 **[Click here to view the Interactive Dashboard](https://nse-sql-analytics-140423102005.streamlit.app/)**

---

## 🏗️ System Architecture

```text
[ Yahoo Finance API ]
         │
         ▼
[ GitHub Actions (ETL) ]
         │
         │ Daily Scheduled Cron
         ▼
[ Incremental Sync ]
   ON CONFLICT DO NOTHING
         │
         ▼
[ Neon PostgreSQL ]
   Cloud Database
    Star Schema
         │
         ▼
[ SQL Queries via SQLAlchemy ]
         │
         ▼
[ Streamlit Web App ]
         │
         ▼
[ UptimeRobot Keep-Alive ]
```

### Architecture Components

1. **ETL Pipeline**
   - A scheduled GitHub Action runs daily.
   - Fetches OHLCV data for NIFTY 50 tickers using `yfinance`.
   - Performs incremental synchronization with PostgreSQL.
   - Uses `ON CONFLICT DO NOTHING` to prevent duplicate records.

2. **Database Layer**
   - Hosted on **Neon.tech PostgreSQL**.
   - Uses a star-schema-inspired structure.
   - Main tables:
     - `dim_companies`
     - `fact_stock_prices`
     - `fact_index_prices`

3. **Analytics UI**
   - Built using **Streamlit**.
   - Uses **Plotly** for interactive financial visualizations.
   - Provides:
     - Interactive candlestick charts
     - SMA 20 / 50 / 200 moving averages
     - Normalized relative performance
     - Daily alpha calculations
     - Stock and benchmark comparisons

4. **Uptime Monitoring**
   - **UptimeRobot** is used to periodically access the application.
   - Helps prevent free-tier inactivity and keeps the dashboard available.

---

## 📊 Database Schema

### Company Dimension Table

```sql
CREATE TABLE dim_companies (
    ticker VARCHAR(20) PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    sector VARCHAR(50) NOT NULL,
    industry VARCHAR(50) NOT NULL
);
```

### Stock Prices Fact Table

```sql
CREATE TABLE fact_stock_prices (
    trade_date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL
        REFERENCES dim_companies(ticker)
        ON DELETE CASCADE,
    open_price NUMERIC(10, 2),
    high_price NUMERIC(10, 2),
    low_price NUMERIC(10, 2),
    close_price NUMERIC(10, 2),
    adj_close NUMERIC(10, 2),
    volume BIGINT,
    PRIMARY KEY (trade_date, ticker)
);
```

### Index Prices Fact Table

```sql
CREATE TABLE fact_index_prices (
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
```

---

## 📁 Project Structure

```text
nse-sql-analytics/
│
├── .github/
│   └── workflows/
│       └── etl.yml
│
├── dashboard.py
├── fetch_data.py
├── ingest_db.py
├── dim_companies.csv
├── fact_index_prices.csv
├── fact_stock_prices.csv
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 🛠️ Tech Stack & Dependencies

| Category | Technology |
|---|---|
| Programming Language | Python 3.10+ |
| Data Processing | Pandas |
| Database ORM / Connectivity | SQLAlchemy |
| Database | PostgreSQL |
| Cloud Database | Neon.tech |
| Data Source | Yahoo Finance / `yfinance` |
| Visualization | Plotly |
| Dashboard | Streamlit |
| Automation | GitHub Actions |
| Monitoring | UptimeRobot |
| Configuration | PyYAML |

---

## ⚙️ Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/srj-145/nse-sql-analytics.git
cd nse-sql-analytics
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
```

Activate the environment:

**macOS / Linux**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 4. Configure Environment Variables

Set your PostgreSQL database connection string in your local terminal session:

```bash
export DATABASE_URL="postgresql+psycopg2://<user>:<password>@<host>/<dbname>?sslmode=require"
```

For Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql+psycopg2://<user>:<password>@<host>/<dbname>?sslmode=require"
```

> **Security Note:** Never commit your actual database credentials, passwords, API keys, or `.env` files to GitHub.

### 5. Run the ETL Pipeline

```bash
python3 fetch_data.py
```

Then ingest the data into PostgreSQL:

```bash
python3 ingest_db.py
```

### 6. Run the Local Dashboard

```bash
streamlit run dashboard.py
```

The Streamlit application will normally be available at:

```text
http://localhost:8501
```

---

## 🔄 Automated Data Pipeline

The project uses GitHub Actions to automate the daily data ingestion process.

The workflow follows this sequence:

```text
Yahoo Finance
      │
      ▼
fetch_data.py
      │
      ▼
OHLCV Data
      │
      ▼
ingest_db.py
      │
      ▼
Neon PostgreSQL
      │
      ▼
Streamlit Dashboard
```

The incremental loading strategy ensures that existing records are not duplicated while newly available market data is added to the database.

---

## 📈 Analytics & Dashboard Features

The dashboard is designed to provide an interactive view of NIFTY 50 market data.

### Market Data

- Daily Open, High, Low, and Close prices
- Adjusted closing prices
- Trading volume
- Historical price data
- NIFTY 50 benchmark data

### Technical Analysis

- 20-day Simple Moving Average (SMA)
- 50-day Simple Moving Average (SMA)
- 200-day Simple Moving Average (SMA)
- Interactive candlestick charts

### Relative Performance

The dashboard allows users to compare individual stocks against benchmark indices using normalized performance measurements.

### Alpha Analysis

Daily alpha calculations provide a way to compare the daily performance of an individual stock against the selected benchmark.

---

## 🗄️ Data Model

The database separates company metadata from time-series market data.

```text
                    ┌─────────────────────┐
                    │    dim_companies     │
                    ├─────────────────────┤
                    │ ticker (PK)          │
                    │ company_name         │
                    │ sector               │
                    │ industry             │
                    └──────────┬──────────┘
                               │
                               │ Foreign Key
                               ▼
                    ┌─────────────────────┐
                    │ fact_stock_prices    │
                    ├─────────────────────┤
                    │ trade_date (PK)      │
                    │ ticker (PK/FK)       │
                    │ open_price           │
                    │ high_price           │
                    │ low_price            │
                    │ close_price          │
                    │ adj_close            │
                    │ volume               │
                    └─────────────────────┘

                    ┌─────────────────────┐
                    │ fact_index_prices    │
                    ├─────────────────────┤
                    │ trade_date (PK)      │
                    │ index_name (PK)      │
                    │ open_price           │
                    │ high_price           │
                    │ low_price            │
                    │ close_price          │
                    │ adj_close            │
                    │ volume               │
                    └─────────────────────┘
```

---

## 🔐 Security Considerations

The application uses environment variables for sensitive database credentials.

Do **not** hard-code credentials directly into Python files.

Recommended approach:

```text
DATABASE_URL
```

should be stored as:

- A local environment variable during development
- A GitHub Actions Secret for automated ETL
- A Streamlit Secret for Streamlit Cloud deployment

Never commit:

```text
.env
secrets.toml
database passwords
API keys
private credentials
```

to the repository.

---

## ☁️ Deployment

### Streamlit Cloud

The dashboard can be deployed using Streamlit Cloud.

The deployed application is available at:

**[NSE NIFTY 50 Analytics Dashboard](https://nse-sql-analytics-140423102005.streamlit.app/)**

### PostgreSQL

The production database is hosted using **Neon PostgreSQL**.

### GitHub Actions

GitHub Actions handles the scheduled ETL process, allowing market data to be updated automatically without manually running the data pipeline.

---

## 🎯 Project Objectives

The primary objectives of this project are to:

- Build an end-to-end financial data pipeline.
- Collect and process NIFTY 50 market data.
- Store structured financial data using PostgreSQL.
- Apply relational database and SQL concepts to real-world financial data.
- Automate data ingestion using GitHub Actions.
- Build interactive financial analytics using Streamlit and Plotly.
- Compare individual stock performance against benchmark indices.
- Demonstrate practical use of ETL, databases, SQL, Python, and data visualization.

---

## 💡 Key Concepts Demonstrated

This project demonstrates practical experience with:

- ETL Pipelines
- Data Engineering
- SQL
- PostgreSQL
- Database Design
- Star Schema / Dimensional Modeling
- Relational Data Modeling
- Incremental Data Loading
- Cloud Databases
- Financial Data Analysis
- Time-Series Data
- Technical Indicators
- Data Visualization
- Python
- Streamlit
- Plotly
- GitHub Actions
- CI/CD Automation
- Cloud Deployment

---

## ⚠️ Disclaimer

This project is intended for **educational and analytical purposes only**.

The information and visualizations provided by this application should not be considered financial advice or a recommendation to buy, sell, or hold any security.

Market data is obtained from third-party sources and may contain delays, inaccuracies, or inconsistencies.

Users should independently verify financial information before making any investment decisions.

---

## 📜 License

This project is open-source and available under the **MIT License**.

See the [`LICENSE`](LICENSE) file for the complete license text.

---

## 👤 Author

**Suriti Joshi**

GitHub: [@srj-145](https://github.com/srj-145)

---

## 🔗 Project Links

- **Live Dashboard:** https://nse-sql-analytics-140423102005.streamlit.app/
- **GitHub Repository:** https://github.com/srj-145/nse-sql-analytics
- **Data Source:** Yahoo Finance
- **Database:** Neon PostgreSQL
- **Dashboard:** Streamlit

---

⭐ If you find this project useful, consider giving the repository a star!
