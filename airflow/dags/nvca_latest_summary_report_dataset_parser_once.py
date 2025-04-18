from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.utils.dates import days_ago
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from pathlib import Path
from io import BytesIO
from services.s3 import S3FileManager
from services.mistral_orc_processing import pdf_mistralocr_converter
from services.vector_store import upsert_vectors
from services.chunk_strategy import semantic_chunking
from services.vector_store import get_embedding
import uuid
import json

@task
def get_input_files(**context):
    states = json.loads(Variable.get("VC_STATE_LIST"))
    base_root = "nvca-pdfs"
    file_name = "extracted_data.md"

    return [
        {"base_path": f"{base_root}/{state}/mistral", "file_name": file_name}
        for state in states
    ]

@task
def get_existing_markdown_file(file_info: dict) -> str:
    base_path = file_info["base_path"]
    file_name = file_info["file_name"]

    AWS_BUCKET_NAME = Variable.get("AWS_BUCKET_NAME")
    full_key = f"{base_path}/{file_name}"

    # Optional: Check if file exists in S3
    s3 = S3Hook(aws_conn_id="aws_default")
    if not s3.check_for_key(full_key, bucket_name=AWS_BUCKET_NAME):
        raise FileNotFoundError(f"❌ Markdown file not found: s3://{AWS_BUCKET_NAME}/{full_key}")

    print(f"📄 Using existing markdown: s3://{AWS_BUCKET_NAME}/{full_key}")
    return full_key

# ─── Task 3: Push to Pinecone ───────────────────────────────────────────────
from services.vector_store import connect_to_pinecone_index
@task
def push_to_pinecone(markdown_file_path: str):
    print(f"📄 Embedding and uploading: {markdown_file_path}")

    s3_obj = S3FileManager(Variable.get("AWS_BUCKET_NAME"), markdown_file_path)
    content = s3_obj.load_s3_file_content(markdown_file_path)
    if not content:
        print(f"⚠️ Empty content in {markdown_file_path}, skipping.")
        return

    state = Path(markdown_file_path).parts[2] if len(Path(markdown_file_path).parts) > 2 else "unknown"
    file_name = Path(markdown_file_path).stem

    chunks = semantic_chunking(content, max_sentences=5)
    print(f"🔍 Created {len(chunks)} semantic chunks.")

    docs = [
        {
            "id": f"{state}_{file_name}_chunk_{i}_{str(uuid.uuid4())[:8]}",
            "values": get_embedding(chunk),
            "metadata": {
                "state": state,
                "source_file": markdown_file_path,
                "chunk_id": i,
                "text_preview": chunk[:150]
            }
        }
        for i, chunk in enumerate(chunks)
    ]

    index = connect_to_pinecone_index()
    upsert_vectors(index, docs, namespace='nvdia_quarterly_reports')
    print(f"✅ Uploaded {len(docs)} vectors for `{state}`")

with DAG(
    dag_id="ocr_from_s3_selected_files_once",
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
    tags=["vc_reports", "scraping", "markdown", "venture-scope"],
    max_active_runs=1,
    max_active_tasks=1
) as dag:
    input_files = get_input_files()
    markdown_files = get_existing_markdown_file.expand(file_info=input_files)
    push_to_pinecone.expand(markdown_file_path=markdown_files)