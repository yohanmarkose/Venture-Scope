import json
import io
from pathlib import Path
from airflow import DAG
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.utils.dates import days_ago

from services.s3 import S3FileManager
from services.mistral_orc_processing import pdf_mistralocr_converter
from services.chunk_strategy import semantic_chunking
from services.vector_store import create_pinecone_vector_store

@dag(
    dag_id='chatbots_personalities_source_parser_once',
    default_args={
        'owner': 'airflow',
        'start_date': days_ago(1),
        'retries': 1
    },
    schedule_interval='@once',
    catchup=False,
    tags=["ocr", "markdown", "chatbots","pinecone","expertschatbot",'venture-scope'],
    max_active_runs=1,
    max_active_tasks=2
)
def process_existing_pdfs():

    @task
    def get_s3_pdfs():
        return json.loads(Variable.get("CHATBOT_SOURCE_PDF_FILES", default_var='["chatbot_source_books/BenHorowitz/BenHorowit_a16z_TheHardThingAboutHardThings.pdf"]'))

    @task
    def process_and_index(s3_path: str) -> str:
        print(f"🔍 Starting OCR + Pinecone for: {s3_path}")
        AWS_BUCKET_NAME = Variable.get("AWS_BUCKET_NAME")
        s3_obj = S3FileManager(AWS_BUCKET_NAME, s3_path)

        # Load PDF from S3
        pdf_file = s3_obj.load_s3_pdf(s3_path)
        pdf_stream = io.BytesIO(pdf_file)

        # Define output path
        output_path = f"{Path(s3_path).parent}/mistral"
        md_file_path, _ = pdf_mistralocr_converter(pdf_stream, output_path, s3_obj)

        # Load markdown output
        print(f"📄 Loading markdown file from S3: {md_file_path}")
        markdown_text = s3_obj.load_s3_file_content(md_file_path)

        # Chunk and embed
        print("🔧 Chunking markdown content...")
        chunks = semantic_chunking(markdown_text, max_sentences=10)
        print(f"🧠 Total chunks: {len(chunks)}")

        print("📤 Uploading vectors to Pinecone...")
        create_pinecone_vector_store(md_file_path, chunks)

        return f"✅ Finished processing and indexing: {s3_path}"

    # Chain tasks
    process_and_index.expand(s3_path=get_s3_pdfs())


process_existing_pdfs()