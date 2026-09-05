import sqlite3
import pandas as pd

# Increase pandas display options for wide SQL outputs
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)

conn = sqlite3.connect("nse_portfolio.db")

print("=" * 80)
print("QUERY 1: Daily Returns Calculation using LAG()")
print("=" * 80)
query_1 = """
WITH daily_returns AS (
    SELECT 
        s.trade_date,
        c.company_name,
        s.ticker,
        s.close_price,
        LAG(s.close_price, 1) OVER (PARTITION BY s.ticker ORDER BY s.trade_date) AS prev_close
    FROM fact_stock_prices s
    JOIN dim_companies c ON s.ticker = c.ticker
)
SELECT 
    trade_date,
    company_name,
    ticker,
    close_price,
    prev_close,
    ROUND(((close_price - prev_close) / prev_close) * 100, 2) AS daily_return_pct
FROM daily_returns
WHERE prev_close IS NOT NULL
ORDER BY ticker, trade_date DESC
LIMIT 10;
"""
df1 = pd.read_sql_query(query_1, conn)
print(df1)

print("\n" + "=" * 80)
print(
    "QUERY 2: Monthly Stock Performance Ranking within Sectors using RANK()"
)
print("=" * 80)
query_2 = """
WITH monthly_prices AS (
    SELECT 
        c.sector,
        c.company_name,
        s.ticker,
        strftime('%Y-%m', s.trade_date) AS month,
        FIRST_VALUE(s.close_price) OVER (
            PARTITION BY s.ticker, strftime('%Y-%m', s.trade_date) 
            ORDER BY s.trade_date
        ) AS month_start_price,
        LAST_VALUE(s.close_price) OVER (
            PARTITION BY s.ticker, strftime('%Y-%m', s.trade_date) 
            ORDER BY s.trade_date 
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS month_end_price
    FROM fact_stock_prices s
    JOIN dim_companies c ON s.ticker = c.ticker
),
distinct_monthly_returns AS (
    SELECT DISTINCT
        month,
        sector,
        company_name,
        ticker,
        ROUND(((month_end_price - month_start_price) / month_start_price) * 100, 2) AS monthly_return_pct
    FROM monthly_prices
)
SELECT 
    month,
    sector,
    company_name,
    monthly_return_pct,
    RANK() OVER (PARTITION BY month ORDER BY monthly_return_pct DESC) AS overall_rank_in_month
FROM distinct_monthly_returns
WHERE month = '2024-01'
ORDER BY overall_rank_in_month;
"""
df2 = pd.read_sql_query(query_2, conn)
print(df2)

print("\n" + "=" * 80)
print("QUERY 3: 30-Day Simple Moving Average (SMA) & Price Volatility Spread")
print("=" * 80)
query_3 = """
SELECT 
    s.trade_date,
    c.company_name,
    s.close_price,
    ROUND(AVG(s.close_price) OVER (
        PARTITION BY s.ticker 
        ORDER BY s.trade_date 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 2) AS moving_avg_30d,
    ROUND(
        MAX(s.close_price) OVER (
            PARTITION BY s.ticker 
            ORDER BY s.trade_date 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) - 
        MIN(s.close_price) OVER (
            PARTITION BY s.ticker 
            ORDER BY s.trade_date 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ), 2
    ) AS volatility_spread_30d
FROM fact_stock_prices s
JOIN dim_companies c ON s.ticker = c.ticker
WHERE s.ticker = 'RELIANCE.NS'
ORDER BY s.trade_date DESC
LIMIT 12;
"""
df3 = pd.read_sql_query(query_3, conn)
print(df3)

print("\n" + "=" * 80)
print("QUERY 4: Alpha Over Benchmark (Stock Return vs. NIFTY 50 Return)")
print("=" * 80)
query_4 = """
WITH stock_returns AS (
    SELECT 
        trade_date,
        ticker,
        close_price,
        LAG(close_price, 1) OVER (PARTITION BY ticker ORDER BY trade_date) AS prev_stock_close
    FROM fact_stock_prices
),
index_returns AS (
    SELECT 
        trade_date,
        close_price AS index_close,
        LAG(close_price, 1) OVER (ORDER BY trade_date) AS prev_index_close
    FROM fact_index_prices
)
SELECT 
    s.trade_date,
    s.ticker,
    ROUND(((s.close_price - s.prev_stock_close) / s.prev_stock_close) * 100, 2) AS stock_daily_return_pct,
    ROUND(((i.index_close - i.prev_index_close) / i.prev_index_close) * 100, 2) AS nifty_daily_return_pct,
    ROUND(
        (((s.close_price - s.prev_stock_close) / s.prev_stock_close) - 
         ((i.index_close - i.prev_index_close) / i.prev_index_close)) * 100, 2
    ) AS alpha_over_nifty_pct
FROM stock_returns s
JOIN index_returns i ON s.trade_date = i.trade_date
WHERE s.ticker = 'TCS.NS' AND s.prev_stock_close IS NOT NULL
ORDER BY s.trade_date DESC
LIMIT 12;
"""
df4 = pd.read_sql_query(query_4, conn)
print(df4)

conn.close()