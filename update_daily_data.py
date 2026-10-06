import os
import datetime
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL environment variable is not set.")
    exit(0)

# Enforce psycopg2 dialect for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)

TOP_25_COMPANIES = [
    {"ticker": "RELIANCE.NS", "company_name": "Reliance Industries Ltd", "sector": "Energy & Industrials"},
    {"ticker": "TCS.NS", "company_name": "Tata Consultancy Services Ltd", "sector": "Information Technology"},
    {"ticker": "HDFCBANK.NS", "company_name": "HDFC Bank Ltd", "sector": "Financial Services"},
    {"ticker": "ICICIBANK.NS", "company_name": "ICICI Bank Ltd", "sector": "Financial Services"},
    {"ticker": "INFY.NS", "company_name": "Infosys Ltd", "sector": "Information Technology"},
    {"ticker": "BHARTIARTL.NS", "company_name": "Bharti Airtel Ltd", "sector": "Telecommunication"},
    {"ticker": "ITC.NS", "company_name": "ITC Ltd", "sector": "Consumer Goods"},
    {"ticker": "SBIN.NS", "company_name": "State Bank of India", "sector": "Financial Services"},
    {"ticker": "LTIM.NS", "company_name": "LTIMindtree Ltd", "sector": "Information Technology"},
    {"ticker": "LT.NS", "company_name": "Larsen & Toubro Ltd", "sector": "Construction & Engineering"},
    {"ticker": "HINDUNILVR.NS", "company_name": "Hindustan Unilever Ltd", "sector": "Consumer Goods"},
    {"ticker": "AXISBANK.NS", "company_name": "Axis Bank Ltd", "sector": "Financial Services"},
    {"ticker": "KOTAKBANK.NS", "company_name": "Kotak Mahindra Bank Ltd", "sector": "Financial Services"},
    {"ticker": "M&M.NS", "company_name": "Mahindra & Mahindra Ltd", "sector": "Automobile"},
    {"ticker": "MARUTI.NS", "company_name": "Maruti Suzuki India Ltd", "sector": "Automobile"},
    {"ticker": "SUNPHARMA.NS", "company_name": "Sun Pharmaceutical Industries Ltd", "sector": "Healthcare & Pharma"},
    {"ticker": "TATAMOTORS.NS", "company_name": "Tata Motors Ltd", "sector": "Automobile"},
    {"ticker": "NTPC.NS", "company_name": "NTPC Ltd", "sector": "Power & Energy"},
    {"ticker": "ONGC.NS", "company_name": "Oil & Natural Gas Corporation Ltd", "sector": "Energy"},
    {"ticker": "POWERGRID.NS", "company_name": "Power Grid Corporation of India Ltd", "sector": "Power & Energy"},
    {"ticker": "TITAN.NS", "company_name": "Titan Company Ltd", "sector": "Consumer Goods"},
    {"ticker": "ULTRACEMCO.NS", "company_name": "UltraTech Cement Ltd", "sector": "Construction Materials"},
    {"ticker": "BAJFINANCE.NS", "company_name": "Bajaj Finance Ltd", "sector": "Financial Services"},
    {"ticker": "ADANIENT.NS", "company_name": "Adani Enterprises Ltd", "sector": "Metals & Mining"},
    {"ticker": "WIPRO.NS", "company_name": "Wipro Ltd", "sector": "Information Technology"}
]

def clean_val(val, val_type=float):
    if pd.isna(val) or val is None:
        return None
    try:
        if val_type == int:
            return int(val)
        return round(float(val), 2)
    except (ValueError, TypeError):
        return None

def seed_companies():
    upsert_sql = text("""
        INSERT INTO dim_companies (ticker, company_name, sector)
        VALUES (:ticker, :company_name, :sector)
        ON CONFLICT (ticker) DO UPDATE 
        SET company_name = EXCLUDED.company_name, sector = EXCLUDED.sector;
    """)
    try:
        with engine.begin() as conn:
            for company in TOP_25_COMPANIES:
                conn.execute(upsert_sql, company)
        print("Successfully verified/seeded top 25 companies into dim_companies table.")
    except Exception as e:
        print(f"Error seeding companies: {e}")

def get_latest_date():
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT MAX(trade_date) FROM fact_stock_prices;")).scalar()
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def update_data():
    # Ensure all 25 companies are present in dim_companies
    seed_companies()

    latest_date = get_latest_date()
    today = datetime.date.today()
    
    if latest_date is None:
        start_date = datetime.date(2024, 1, 1)
    else:
        start_date = latest_date + datetime.timedelta(days=1)
        
    if start_date >= today:
        print("Data is already up to date!")
        return

    print(f"Fetching missing data from {start_date} to {today}...")

    try:
        tickers_df = pd.read_sql("SELECT ticker FROM dim_companies;", engine)
        tickers = tickers_df['ticker'].tolist()
    except Exception as e:
        print(f"Error loading tickers: {e}")
        return

    if not tickers:
        print("No tickers found in dim_companies table.")
        return

    # Fetch stock prices
    try:
        data = yf.download(tickers, start=start_date, end=today + datetime.timedelta(days=1), group_by='ticker', auto_adjust=False, progress=False)
    except Exception as e:
        print(f"Error fetching yfinance data: {e}")
        return

    stock_records = []
    if not data.empty:
        for ticker in tickers:
            try:
                if len(tickers) > 1 and ticker in data.columns.levels[0]:
                    df_ticker = data[ticker].dropna(how='all').reset_index()
                else:
                    df_ticker = data.dropna(how='all').reset_index()

                if isinstance(df_ticker.columns, pd.MultiIndex):
                    df_ticker.columns = df_ticker.columns.get_level_values(0)

                for _, row in df_ticker.iterrows():
                    close_p = clean_val(row.get('Close'))
                    if close_p is None:
                        continue

                    trade_date = pd.to_datetime(row['Date']).date()
                    if trade_date >= today:
                        continue

                    stock_records.append({
                        'trade_date': trade_date,
                        'ticker': ticker,
                        'open_price': clean_val(row.get('Open')),
                        'high_price': clean_val(row.get('High')),
                        'low_price': clean_val(row.get('Low')),
                        'close_price': close_p,
                        'adj_close': clean_val(row.get('Adj Close')),
                        'volume': clean_val(row.get('Volume'), int)
                    })
            except Exception as e:
                print(f"Error processing ticker {ticker}: {e}")

    if stock_records:
        df_stock = pd.DataFrame(stock_records)
        insert_sql = text("""
            INSERT INTO fact_stock_prices (trade_date, ticker, open_price, high_price, low_price, close_price, adj_close, volume)
            VALUES (:trade_date, :ticker, :open_price, :high_price, :low_price, :close_price, :adj_close, :volume)
            ON CONFLICT (trade_date, ticker) DO NOTHING;
        """)
        try:
            with engine.begin() as conn:
                conn.execute(insert_sql, df_stock.to_dict(orient='records'))
            print(f"Inserted {len(stock_records)} stock price records.")
        except Exception as e:
            print(f"Error executing stock insert query: {e}")

    # Fetch NIFTY 50 Index data
    try:
        index_data = yf.download("^NSEI", start=start_date, end=today + datetime.timedelta(days=1), auto_adjust=False, progress=False).reset_index()
        if isinstance(index_data.columns, pd.MultiIndex):
            index_data.columns = index_data.columns.get_level_values(0)

        index_records = []
        for _, row in index_data.iterrows():
            close_p = clean_val(row.get('Close'))
            if close_p is None:
                continue

            trade_date = pd.to_datetime(row['Date']).date()
            if trade_date >= today:
                continue

            index_records.append({
                'trade_date': trade_date,
                'index_name': 'NIFTY 50',
                'open_price': clean_val(row.get('Open')),
                'high_price': clean_val(row.get('High')),
                'low_price': clean_val(row.get('Low')),
                'close_price': close_p,
                'adj_close': clean_val(row.get('Adj Close')),
                'volume': clean_val(row.get('Volume'), int)
            })

        if index_records:
            df_index = pd.DataFrame(index_records)
            insert_index_sql = text("""
                INSERT INTO fact_index_prices (trade_date, index_name, open_price, high_price, low_price, close_price, adj_close, volume)
                VALUES (:trade_date, :index_name, :open_price, :high_price, :low_price, :close_price, :adj_close, :volume)
                ON CONFLICT (trade_date, index_name) DO NOTHING;
            """)
            with engine.begin() as conn:
                conn.execute(insert_index_sql, df_index.to_dict(orient='records'))
            print(f"Inserted {len(index_records)} index records.")
    except Exception as e:
        print(f"Error processing index data: {e}")

if __name__ == "__main__":
    update_data()
