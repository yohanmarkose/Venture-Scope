from io import BytesIO
import requests
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.models import Variable

def upload_pdf_to_s3(pdf_url: str, state: str) -> str:
    """
    Upload PDF to S3 using direct URL and return the S3 path.
    """
    AWS_BUCKET_NAME = Variable.get("AWS_BUCKET_NAME")
    filename = pdf_url.split("/")[-1]
    s3_path = f"nvca-pdfs/{state}/{filename}"

    response = requests.get(pdf_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch PDF from {pdf_url}. Status: {response.status_code}")

    pdf_content = BytesIO(response.content)

    s3_hook = S3Hook(aws_conn_id='aws_default')
    s3_hook.load_file_obj(
        file_obj=pdf_content,
        bucket_name=AWS_BUCKET_NAME,
        key=s3_path,
        replace=True
    )

    print(f"✅ Uploaded {state} PDF to S3: s3://{AWS_BUCKET_NAME}/{s3_path}")
    return s3_path