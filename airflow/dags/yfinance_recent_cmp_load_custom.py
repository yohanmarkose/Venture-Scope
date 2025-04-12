from airflow import DAG
from airflow.decorators import task
from airflow.utils.dates import days_ago
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from snowflake.connector.pandas_tools import write_pandas

import yfinance as yf
import numpy as np
import pandas as pd

@task
def get_conf(**context):
    conf = context["dag_run"].conf
    return {
        "company": conf.get("company", "Nvidia"),
        "ticker": conf.get("ticker", "NVDA")
    }

@task
def fetch_and_upload_to_snowflake(config: dict):
    company = config["company"]
    ticker = config["ticker"]
    print(f"📈 Fetching data for {company} ({ticker})")

    start_date = '2020-01-01'
    stock_data = yf.download(ticker, start=start_date)
    info = yf.Ticker(ticker).info

    shares_outstanding = info.get("sharesOutstanding", np.nan)
    trailing_eps = info.get("trailingEps", np.nan)
    dividend_rate = info.get("dividendRate", np.nan)
    total_debt = info.get("totalDebt", np.nan)
    free_cashflow = info.get("freeCashflow", np.nan)
    total_revenue = info.get("totalRevenue", np.nan)

    df = pd.DataFrame({
        "COMPANY": company,
        "TICKER": ticker,
        "DATE": stock_data.index.normalize().to_numpy(),
        "OPEN": stock_data['Open'].values,
        "HIGH": stock_data['High'].values,
        "LOW": stock_data['Low'].values,
        "CLOSE": stock_data['Close'].values,
        "VOLUME": stock_data['Volume'].values,
        "MARKETCAP": stock_data['Close'].values * shares_outstanding if not np.isnan(shares_outstanding) else np.nan,
        "EPS": trailing_eps,
        "PERATIO": stock_data['Close'].values / trailing_eps if not np.isnan(trailing_eps) else np.nan,
        "BETA": info.get("beta", np.nan),
        "DIVIDENDYIELD": (dividend_rate * shares_outstanding) / (stock_data['Close'].values * shares_outstanding) if not np.isnan(dividend_rate) else np.nan,
        "ENTERPRISEVALUE": (stock_data['Close'].values * shares_outstanding) + total_debt - free_cashflow if not np.isnan(total_debt) else np.nan,
        "PRICETOSALESTRAILING12MONTHS": (stock_data['Close'].values * shares_outstanding) / total_revenue if not np.isnan(total_revenue) else np.nan,
    })

    df = df.astype(object).where(pd.notnull(df), None)

    table_name = "NVIDIA_VALUATION_V2"
    hook = SnowflakeHook(snowflake_conn_id="snowflake_default")
    conn = hook.get_conn()

    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {hook.schema}.{table_name} (
        COMPANY STRING,
        TICKER STRING,
        DATE DATE,
        OPEN FLOAT,
        HIGH FLOAT,
        LOW FLOAT,
        CLOSE FLOAT,
        VOLUME FLOAT,
        MARKETCAP FLOAT,
        EPS FLOAT,
        PERATIO FLOAT,
        BETA FLOAT,
        DIVIDENDYIELD FLOAT,
        ENTERPRISEVALUE FLOAT,
        PRICETOSALESTRAILING12MONTHS FLOAT
    );
    """
    conn.cursor().execute(create_sql)

    success, nchunks, nrows, _ = write_pandas(
        conn=conn,
        df=df,
        table_name=table_name,
        schema=hook.schema,
        database=hook.database,
        overwrite=False
    )

    print(f"✅ Inserted {nrows} rows into {table_name}.")

# Define the DAG
with DAG(
    dag_id="stock_valuation_to_snowflake",
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
    tags=["stock", "snowflake"]
) as dag:
    config = get_conf()
    fetch_and_upload_to_snowflake(config)