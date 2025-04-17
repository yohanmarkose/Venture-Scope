from io import BytesIO
import base64
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.models import Variable
from datetime import datetime
from services.snowflake.ticker_file import fetch_all_us_listed_companies

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


with DAG(
    dag_id='custom_marketanalysis_raw_data_snowflake',
    default_args=default_args,
    tags=['snowflake','dataload','market_analysis','freecompanydatset','marketplace'],
    description='Loads or reloads snowflakes tables dataset from Snowflake Marketplace for Freecompanydataset',
    schedule_interval=None,
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

    # End task
    end = EmptyOperator(task_id='end')

    # DAG flow
    start >> scraping_cmp_ticker_file >> upload_to_s3 >> end