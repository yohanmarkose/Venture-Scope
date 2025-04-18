import os
import uuid
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from services.s3 import S3FileManager
from services.vector_store import upsert_vectors  # assumes this matches your previous upsert_vectors
from pathlib import Path
from airflow.models import Variable

# ─── Load Env and Keys ──────────────────────────────────────────────────────
load_dotenv()

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
PINECONE_NAMESPACE = 'nvdia_quarterly_reports'
BASE_PATH = f"nvca-pdfs/{State}/mistral/" 

s3 = S3FileManager(AWS_BUCKET_NAME)

def load_mistral_files():
    print("📁 Listing markdown files from:", BASE_PATH)
    files = s3.list_s3_files(BASE_PATH)
    return [f for f in files if f.endswith(".md") or f.endswith(".txt")]


def embed_and_upsert(file_path):
    content = s3.load_s3_file_content(file_path)
    if not content:
        print(f"⚠️ Empty content in {file_path}, skipping.")
        return

    state = Path(file_path).parts[2] if len(Path(file_path).parts) > 2 else "unknown"
    file_name = Path(file_path).stem

    # Split content
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(content)

    # Generate embeddings
    embedder = OpenAIEmbeddings()
    docs = [
        {
            "id": f"{state}_{file_name}_chunk_{i}_{str(uuid.uuid4())[:8]}",
            "values": embedder.embed_query(chunk),
            "metadata": {
                "state": state,
                "source_file": file_path,
                "chunk_id": i,
                "text_preview": chunk[:150]  # optional for quick preview in UI/debug
            }
        }
        for i, chunk in enumerate(chunks)
    ]

    # Upload
    print(f"📌 Uploading {len(docs)} chunks for `{state}` into Pinecone...")
    upsert_vectors(docs, namespace=PINECONE_NAMESPACE)
    print(f"✅ Uploaded: {file_path}\n")

# ─── Main Runner ────────────────────────────────────────────────────────────
def main():
    files = load_mistral_files()
    for file_path in files:
        embed_and_upsert(file_path)

if __name__ == "__main__":
    main()