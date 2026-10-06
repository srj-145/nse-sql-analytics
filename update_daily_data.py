import os
import datetime
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

engine = create_engine(DATABASE_URL)

def get_latest_date():
    with engine.connect() as conn:
        return conn.execute(text("SELECT MAX(trade_date) FROM fact_stock_prices;")).scalar()

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

    tickers_df = pd.read_sql("SELECT ticker FROM dim_companies;", engine)
    tickers = tickers_df['ticker'].tolist()

    if not tickers:
        print("No tickers found in dim_companies table.")
        return

    # Fetch stock prices
    data = yf.download(tickers, start=start_date, end=today + datetime.timedelta(days=1), group_by='ticker', auto_adjust=False, progress=False)

    stock_records = []
    for ticker in tickers:
        try:
            df_ticker = data[ticker].dropna(how='all').reset_index() if len(tickers) > 1 else data.dropna(how='all').reset_index()
            if isinstance(df_ticker.columns, pd.MultiIndex):
                df_ticker.columns = df_ticker.columns.get_level_values(0)
            
            for _, row in df_ticker.iterrows():
                if pd.isna(row.get('Close')):
                    continue
                stock_records.append({
                    'trade_date': pd.to_datetime(row['Date']).date(),
                    'ticker': ticker,
                    'open_price': round(float(row['Open']), 2),
                    'high_price': round(float(row['High']), 2),
                    'low_price': round(float(row['Low']), 2),
                    'close_price': round(float(row['Close']), 2),
                    'adj_close': round(float(row['Adj Close']), 2),
                    'volume': int(row['Volume'])
                })
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    if stock_records:
        df_stock = pd.DataFrame(stock_records)
        insert_sql = text("""
            INSERT INTO fact_stock_prices (trade_date, ticker, open_price, high_price, low_price, close_price, adj_close, volume)
            VALUES (:trade_date, :ticker, :open_price, :high_price, :low_price, :close_price, :adj_close, :volume)
            ON CONFLICT (trade_date, ticker) DO NOTHING;
        """)
        with engine.begin() as conn:
            conn.execute(insert_sql, df_stock.to_dict(orient='records'))
        print(f"Processed {len(stock_records)} stock price records.")

    # Fetch NIFTY 50 Index data
    try:
        index_data = yf.download("^NSEI", start=start_date, end=today + datetime.timedelta(days=1), auto_adjust=False, progress=False).reset_index()
        if isinstance(index_data.columns, pd.MultiIndex):
            index_data.columns = index_data.columns.get_level_values(0)
        
        index_records = []
        for _, row in index_data.iterrows():
            if pd.isna(row.get('Close')):
                continue
            index_records.append({
                'trade_date': pd.to_datetime(row['Date']).date(),
                'index_name': 'NIFTY 50',
                'open_price': round(float(row['Open']), 2),
                'high_price': round(float(row['High']), 2),
                'low_price': round(float(row['Low']), 2),
                'close_price': round(float(row['Close']), 2),
                'adj_close': round(float(row['Adj Close']), 2),
                'volume': int(row['Volume'])
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
            print(f"Processed {len(index_records)} index records.")
    except Exception as e:
        print(f"Error processing index data: {e}")

if __name__ == "__main__":
    update_data()
