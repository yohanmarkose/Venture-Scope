import json
import io
from pathlib import Path
from airflow import DAG
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.utils.dates import days_ago

from services.s3 import S3FileManager
from services.mistral_orc_processing import pdf_mistralocr_converter


@dag(
    dag_id='chatboats_personalities_source_parser_once',
    default_args={
        'owner': 'airflow',
        'start_date': days_ago(1),
        'retries': 1
    },
    schedule_interval='@once',
    catchup=False,
    tags=["vc_reports", "ocr", "markdown","chatboats"],
    max_active_runs=1,
    max_active_tasks=2
)
def process_existing_pdfs():

    @task
    def get_s3_pdfs():
        """
        Return a list of existing S3 PDF paths to process.
        """
        # Option 1: Hardcoded paths (for testing/demo)
        return json.loads(Variable.get("CHATBOT_SOURCE_PDF_FILES", default_var='["chatbot_source_books/BenHorowit.pdf"]'))

    @task
    def process_via_mistral_ocr(s3_path: str) -> str:
        print(f"🔍 Running Mistral OCR for file: {s3_path}")
        AWS_BUCKET_NAME = Variable.get("AWS_BUCKET_NAME")
        s3_obj = S3FileManager(AWS_BUCKET_NAME, s3_path)

        # Load PDF from S3
        pdf_file = s3_obj.load_s3_pdf(s3_path)
        pdf_stream = io.BytesIO(pdf_file)

        # Define output path
        output_path = f"{Path(s3_path).parent}/mistral"
        file_name, content = pdf_mistralocr_converter(pdf_stream, output_path, s3_obj)

        print(f"✅ OCR completed. Markdown saved to: {file_name}")
        return file_name

    # Run OCR for each path
    process_via_mistral_ocr.expand(s3_path=get_s3_pdfs())


process_existing_pdfs()