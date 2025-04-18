import pandas as pd
import snowflake.connector
import yfinance as yf
import numpy as np
import datetime
import time
from snowflake.connector.pandas_tools import write_pandas

from dotenv import load_dotenv
import os

load_dotenv()

conn_params = {
    'user': os.getenv('SNOWFLAKE_USER'),
    'password': os.getenv('SNOWFLAKE_PASSWORD'),
    'account': os.getenv('SNOWFLAKE_ACCOUNT'),
    'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
    'database': os.getenv('SNOWFLAKE_DATABASE'),
    'schema': os.getenv('SNOWFLAKE_SCHEMA'),
    'role': os.getenv('SNOWFLAKE_ROLE')
}

def connect_to_snowflake(params):
    try:
        conn = snowflake.connector.connect(
            user=params['user'],
            password=params['password'],
            account=params['account'],
            warehouse=params['warehouse'],
            database=params['database'],
            schema=params['schema'],
            role=params['role']  # Specify the role if needed
        )
        print("Connected to Snowflake successfully!")
        return conn
    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")
        return None

def create_table_in_snowflake(conn, table_name="LARGE_COMPANY_DATA_FINAL", schema="OPPORTUNITY_ANALYSIS.MARKET_ANALYSIS"):
    create_query = f"""
    CREATE OR REPLACE TABLE {schema}.{table_name} (
        ID VARCHAR,
        COMPANY_NAME VARCHAR,
        INDUSTRY VARCHAR,
        SIZE VARCHAR,
        FOUNDED NUMBER,
        REGION VARCHAR,
        COUNTRY VARCHAR,
        LOCALITY VARCHAR,
        WEBSITE VARCHAR,
        LINKEDIN_URL VARCHAR,
        COMPANY_AGE NUMBER,
        SIZE_CATAGORY VARCHAR,
        PERFORMANCE_CATEGORY VARCHAR,
        PERFORMANCE_SCORE FLOAT,
        T_SYMBOL VARCHAR,
        TICKER VARCHAR,
        CURRENT_PRICE FLOAT,
        MARKET_CAP NUMBER,
        YEARLY_RETURN NUMBER,
        VOLATILITY VARCHAR
    );
    """
    try:
        cursor = conn.cursor()
        cursor.execute(create_query)
        print(f"Table {schema}.{table_name} created or replaced.")
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        cursor.close()

def save_df_to_snowflake(df, table_name="LARGE_COMPANY_DATA_FINAL", database="OPPORTUNITY_ANALYSIS", schema="MARKET_ANALYSIS"):
    conn = connect_to_snowflake(conn_params)
    if conn is None:
        print("❌ Could not connect to Snowflake.")
        return

    try:
        conn.cursor().execute(f"USE DATABASE {database}")
        conn.cursor().execute(f"USE SCHEMA {schema}")

        df.columns = [col.upper() for col in df.columns]

        create_table_in_snowflake(conn, table_name, f"{database}.{schema}")

        # Write data using uppercase column names
        success, nchunks, nrows, _ = write_pandas(conn, df, table_name=table_name, schema=schema)

        if success:
            print(f"✅ Successfully inserted {nrows} rows into {database}.{schema}.{table_name}")
        else:
            print(f"❌ Failed to write DataFrame to Snowflake")

    except Exception as e:
        print(f"❌ Error writing DataFrame to Snowflake: {e}")
    finally:
        conn.close()

def get_company_data():
    """Fetch company data with ticker symbols from Snowflake"""
    conn = connect_to_snowflake(conn_params)
    if conn is None:
        return None
    
    try:
        query = """
        SELECT * FROM LARGE_COMPANIES_WITH_TICKER
        WHERE T_SYMBOL IS NOT NULL
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        print(f"Retrieved {len(df)} companies with ticker symbols")
        return df
    except Exception as e:
        print(f"Error fetching company data: {e}")
        if conn:
            conn.close()
        return None

def get_yfinance_metrics(ticker_list):
    """Get relevant financial metrics for a list of tickers"""
    # Filter out None values
    ticker_list = [t for t in ticker_list if t]
    
    if not ticker_list:
        return pd.DataFrame()
    results = {}
    batch_size = 15
    for i in range(0, len(ticker_list), batch_size):
        batch = ticker_list[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(ticker_list) + batch_size - 1)//batch_size}")
        
        for ticker in batch:
            try:
                ticker_obj = yf.Ticker(ticker)
                info = ticker_obj.info
                hist = ticker_obj.history(period="1y")
                if len(hist) > 0:
                    start_price = hist['Close'].iloc[0]
                    current_price = hist['Close'].iloc[-1]
                    yearly_return = ((current_price - start_price) / start_price) * 100
                    daily_returns = hist['Close'].pct_change().dropna()
                    volatility = daily_returns.std() * 100 * np.sqrt(252)  # Annualized
                else:
                    yearly_return = None
                    volatility = None
                
                # Store the results
                results[ticker] = {
                    'ticker': ticker,
                    'current_price': current_price,
                    'market_cap': info.get('marketCap', None),
                    'yearly_return': yearly_return,
                    'volatility': volatility,
                }
                time.sleep(0.1)  # To avoid hitting the API too fast
                
            except Exception as e:
                print(f"Error processing ticker {ticker}: {e}")
                # Add the ticker to results with None values to maintain the record
                results[ticker] = {
                    'ticker': ticker,
                    'current_price': None,
                    'market_cap': None,
                    'yearly_return': None,
                    'volatility': None
                }
    
    metrics_df = pd.DataFrame.from_dict(results, orient='index')
    return metrics_df


def enhance_company_data_with_yfinance():
    company_df = get_company_data()
    
    if company_df is None or company_df.empty:
        print("No company data available. Exiting.")
        return

    ticker_symbols = company_df['T_SYMBOL'].unique().tolist()
    print(f"Found {len(ticker_symbols)} unique ticker symbols")
    
    metrics_df = get_yfinance_metrics(ticker_symbols)
    
    if metrics_df.empty:
        print("No metrics data retrieved. Exiting.")
        return
    
    enhanced_df = pd.merge(
        company_df,
        metrics_df,
        left_on='T_SYMBOL',
        right_on='ticker',
        how='left'
    )
    enhanced_df = enhanced_df.drop(columns=['ticker'])
    
    print(f"Enhanced dataset has {enhanced_df.shape[1]} columns and {enhanced_df.shape[0]} rows")

    save_df_to_snowflake(enhanced_df)

if __name__ == "__main__":
    # Fetch and enhance company data with yfinance metrics
    enhance_company_data_with_yfinance()