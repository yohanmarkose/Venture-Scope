from io import BytesIO
import requests

from airflow.models import Variable
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

# AWS bucket values
AWS_BUCKET_NAME = Variable.get("AWS_BUCKET_NAME")

def upload_pdf_to_s3(ti, **kwargs):
    """
    Upload PDF from URL directly to S3 based on the task ID and extracted quarter.
    This will push the S3 filename to XCom for downstream tasks.
    """

    pdf_links = ti.xcom_pull(task_ids='pdf_link_collector', key='pdf_link')
    if not pdf_links:
        raise ValueError("No PDF links pulled from XCom.")

    url = pdf_links[0]
    filename = url.split("/")[-1]
    s3_path = f"nvca-pdfs/{filename}"

    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch PDF. Status code: {response.status_code}")

    pdf_content = BytesIO(response.content)

    s3_hook = S3Hook(aws_conn_id='aws_default')
    s3_hook.load_file_obj(
        file_obj=pdf_content,
        bucket_name=AWS_BUCKET_NAME,
        key=s3_path,
        replace=True
    )

    ti.xcom_push(key='s3_pdf_path', value=s3_path)
    print(f"✅ Uploaded to S3: s3://{AWS_BUCKET_NAME}/{s3_path}")
    return f"Uploaded {filename} to S3 bucket {AWS_BUCKET_NAME}/{filename}."