import openai, os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from pathlib import Path
from airflow.models import Variable

from services.chunk_strategy import semantic_chunking
from services.s3 import S3FileManager


# Load environment variables from .env at root
load_dotenv()

# API Keys
PINECONE_API_KEY = Variable.get("PINECONE_API_KEY")
PINECONE_INDEX = Variable.get("PINECONE_CHATBOT_INDEX")
AWS_BUCKET_NAME = Variable.get("AWS_BUCKET_NAME")
openai.api_key= Variable.get("OPENAI_API_KEY")


# Connect to Pinecone
def connect_to_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    if not pc.has_index(PINECONE_INDEX):
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            tags={"environment": "development"}
        )
    return pc.Index(PINECONE_INDEX)

# Read Markdown content from S3
def read_markdown_file(file, s3_obj):
    return s3_obj.load_s3_file_content(file)

# Generate OpenAI embeddings
def get_embedding(text):
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# Upload vectors into Pinecone
def upsert_vectors(index, vectors, namespace="chatbot"):
    try :
        index.upsert(vectors=vectors, namespace=namespace)
    except :
        BATCH_SIZE = 50
        for i in range(0, len(vectors), BATCH_SIZE):
            batch = vectors[i:i + BATCH_SIZE]
            index.upsert(vectors=batch, namespace=namespace)
            print(f"🧠 Uploaded batch {i // BATCH_SIZE + 1} / {len(vectors) // BATCH_SIZE + 1}")

# Create vector store from chunks
def create_pinecone_vector_store(file, chunks):
    index = connect_to_pinecone_index()
    vectors = []

    file_parts = Path(file).parts
    author_tag = file_parts[1] if len(file_parts) > 1 else "unknown"
    identifier = Path(file).stem 

    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        vectors.append((
            f"{author_tag}_{identifier}_chunk_{i}", 
            embedding,
            {"author": author_tag, "source": identifier, "text": chunk}
        ))

    upsert_vectors(index, vectors, namespace=author_tag)
    print(f"🧠 Inserted {len(vectors)} chunks into Pinecone for `{author_tag}`")

def pinecone_main(base_path="chatbot_source_books"):
    index = connect_to_pinecone_index()
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)

    files = [f for f in s3_obj.list_files() if f.endswith(".md")]

    for file in files:
        print(f"📄 Processing: {file}")
        content = read_markdown_file(file, s3_obj)
        chunks = semantic_chunking(content, max_sentences=10)
        print(f"📚 Chunks created: {len(chunks)}")
        create_pinecone_vector_store(file, chunks)
        print("✅ Done.")
        print("--------------------------------------------------")