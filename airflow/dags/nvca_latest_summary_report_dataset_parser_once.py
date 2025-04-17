from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.utils.dates import days_ago
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from pathlib import Path
from io import BytesIO
from services.s3 import S3FileManager
from services.mistral_orc_processing import pdf_mistralocr_converter

@task
def get_input_files(**context):
    conf = context["dag_run"].conf
    base_path = conf.get("base_path")
    pdf_files = conf.get("pdf_files")

    if not base_path or not pdf_files:
        raise ValueError("Missing required params: base_path or pdf_files")

    return [{"base_path": base_path, "file_name": f} for f in pdf_files]

@task
def process_single_pdf(file_info: dict):
    base_path = file_info["base_path"]
    file_name = file_info["file_name"]

    AWS_BUCKET_NAME = Variable.get("AWS_BUCKET_NAME")
    s3 = S3Hook(aws_conn_id="aws_default")
    full_key = f"{base_path}/{file_name}"

    # Download PDF from S3
    print(f"⬇️ Downloading: s3://{AWS_BUCKET_NAME}/{full_key}")
    pdf_bytes = BytesIO()
    s3.get_key(full_key, bucket_name=AWS_BUCKET_NAME).download_fileobj(pdf_bytes)
    pdf_bytes.seek(0)

    # Run Mistral OCR
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    output_path = f"{base_path}/mistral/{Path(file_name).stem}"
    md_file, content = pdf_mistralocr_converter(pdf_bytes, output_path, s3_obj)

    print(f"✅ Processed and saved Markdown to: {md_file}")
    return md_file


with DAG(
    dag_id="ocr_from_s3_selected_files_once",
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
    tags=["vc_reports", "scraping", "markdown"],
    max_active_runs=1,
    max_active_tasks=1
) as dag:

    input_files = get_input_files()
    process_single_pdf.expand(file_info=input_files)