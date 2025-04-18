from io import BytesIO
import base64
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.models import Variable
from datetime import datetime
import logging
from services.snowflake.ticker_file import fetch_all_us_listed_companies
from services.snowflake.yfinace_data_join import enhance_company_data_with_yfinance

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
}

def upload_tickers_to_s3(**kwargs):
    ti = kwargs['ti']
    csv_base64 = ti.xcom_pull(key='ticker_csv_b64', task_ids='scraping_cmp_ticker_file')
    csv_bytes = base64.b64decode(csv_base64)
    buffer = BytesIO(csv_bytes)

    hook = S3Hook(aws_conn_id='aws_default')
    hook.load_file_obj(
        file_obj=buffer,
        key='freecompany_ticker/us_listed_tickers.csv',
        bucket_name=Variable.get("AWS_BUCKET_NAME"),
        replace=True
    )

def snowflake_finaltable():
    logging.info("Starting enhancement process with yfinance.")
    enhance_company_data_with_yfinance()
    logging.info("Enhancement process completed.")


with DAG(
    dag_id='custom_marketanalysis_raw_data_snowflake',
    default_args=default_args,
    tags=['snowflake','dataload','market_analysis','freecompanydatset','marketplace','venture-scope'],
    description='Loads or reloads snowflakes tables dataset from Snowflake Marketplace for Freecompanydataset',
    schedule_interval='0 0 1 1,4,7,10 *',
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    # Start task
    start = EmptyOperator(task_id='start')

    # Scraping ticker file from NASDAQ FTP server
    scraping_cmp_ticker_file = PythonOperator(
        task_id='scraping_cmp_ticker_file',
        python_callable=fetch_all_us_listed_companies,
        dag=dag,
        provide_context=True
    )

    # Ticker file onto S3 bucket
    upload_to_s3 = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_tickers_to_s3,
        provide_context=True
    )


    with TaskGroup("snowflake_load") as snowflake_group:
        # Snowflake task for table creation
        create_snowflake_table = SnowflakeOperator(
        task_id='create_snowflake_table',
        snowflake_conn_id='snowflake_default',
        sql="""
            USE ROLE FIN_ROLE;
            USE WAREHOUSE DBT_WH;

            CREATE OR REPLACE TABLE TICKERS (
                TICKER VARCHAR,
                COMPANY_NAME VARCHAR);""")

        snowflake_stage = SnowflakeOperator(
        task_id='snowflake_stage',
        snowflake_conn_id='snowflake_default',
        sql="""
            CREATE OR REPLACE STAGE ticker_s3_stage
            URL = 's3://{{ var.value.AWS_BUCKET_NAME }}/'
            CREDENTIALS = (
                AWS_KEY_ID = '{{ var.value.AWS_ACCESS_KEY_ID }}',
                AWS_SECRET_KEY = '{{ var.value.AWS_SECRET_ACCESS_KEY }}'
            );""")

        snowflake_format = SnowflakeOperator(
        task_id='snowflake_format',
        snowflake_conn_id='snowflake_default',
        sql="""
        CREATE OR REPLACE FILE FORMAT ticker_csv_format
        TYPE = CSV
        SKIP_HEADER = 1
        FIELD_OPTIONALLY_ENCLOSED_BY='"'
        NULL_IF = ('', 'NULL');""")

        load_to_snowflake = SnowflakeOperator(
            task_id='load_to_snowflake',
            snowflake_conn_id='snowflake_default',
            sql="""
                COPY INTO TICKERS
                FROM @ticker_s3_stage/freecompany_ticker/us_listed_tickers.csv
                FILE_FORMAT = ticker_csv_format;""")

        create_snowflake_table >> snowflake_stage >> snowflake_format >> load_to_snowflake

    
    with TaskGroup("snowflake_rawtableload") as snowflake_rawtableload:

        # 1. Fuzzy match UDF
        snowflake_function = SnowflakeOperator(
            task_id='snowflake_fuzzy_function',
            snowflake_conn_id='snowflake_default',
         sql=r"""
CREATE OR REPLACE FUNCTION FUZZY_SCORE(NAME_A STRING, NAME_B STRING)
RETURNS FLOAT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.8'
PACKAGES = ('rapidfuzz')
HANDLER = 'handler_func'
AS
$$
from rapidfuzz import fuzz

def handler_func(str1, str2):
    return fuzz.partial_ratio(str1, str2)
$$;"""
        )

        # 2. Fuzzy join with ticker info
        snowflake_large_cmp = SnowflakeOperator(
            task_id='snowflake_large_cmp',
            snowflake_conn_id='snowflake_default',
            sql="""
                USE ROLE ACCOUNTADMIN;
                ALTER WAREHOUSE DBT_WH SET WAREHOUSE_SIZE = XSMALL;
                USE ROLE FIN_ROLE;
                USE WAREHOUSE DBT_WH;
                USE SCHEMA OPPORTUNITY_ANALYSIS.MARKET_ANALYSIS;

                CREATE OR REPLACE TABLE opportunity_analysis.market_analysis.large_companies_with_ticker AS
                WITH fuzzy_matches AS (
                    SELECT
                        M.COMPANY_NAME,
                        T.COMPANY_NAME AS TICKER_COMPANY_NAME,
                        T.TICKER,
                        FUZZY_SCORE(LOWER(M.COMPANY_NAME), LOWER(T.COMPANY_NAME)) AS SCORE,
                        SPLIT_PART(TRIM(LOWER(M.COMPANY_NAME)), ' ', 1) AS FIRST_WORD,
                        ROW_NUMBER() OVER (
                            PARTITION BY M.COMPANY_NAME 
                            ORDER BY FUZZY_SCORE(LOWER(M.COMPANY_NAME), LOWER(T.COMPANY_NAME)) DESC
                        ) AS rn
                    FROM opportunity_analysis.market_analysis.large_companies M
                    CROSS JOIN TICKERS T
                    WHERE 
                        FUZZY_SCORE(LOWER(M.COMPANY_NAME), LOWER(T.COMPANY_NAME)) >= 85
                        AND POSITION(SPLIT_PART(TRIM(LOWER(M.COMPANY_NAME)), ' ', 1) IN LOWER(T.COMPANY_NAME)) > 0
                )
                SELECT
                    M.*,
                    fm.TICKER AS T_SYMBOL
                FROM opportunity_analysis.market_analysis.large_companies M
                LEFT JOIN fuzzy_matches fm
                    ON M.COMPANY_NAME = fm.COMPANY_NAME AND fm.rn = 1
                ORDER BY M.COMPANY_NAME;
            """
        )

        # DAG flow inside the TaskGroup
        snowflake_function >> snowflake_large_cmp


    snowflake_analytics = PythonOperator(
        task_id='snowflake_analytics',
        python_callable=snowflake_finaltable,
        provide_context=True
    )

    # End task
    end = EmptyOperator(task_id='end')

    # DAG execution flow        
    start >> scraping_cmp_ticker_file >> upload_to_s3 >> snowflake_group >> snowflake_rawtableload >> snowflake_analytics >> end
