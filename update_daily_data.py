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

def clean_val(val, val_type=float):
    if pd.isna(val) or val is None:
        return None
    try:
        if val_type == int:
            return int(val)
        return round(float(val), 2)
    except (ValueError, TypeError):
        return None

def get_latest_date():
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT MAX(trade_date) FROM fact_stock_prices;")).scalar()
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def update_data():
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
