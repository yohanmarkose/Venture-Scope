import os
import openai
from pinecone import Pinecone
from openai import OpenAI

pinecone = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pinecone.Index(os.getenv("PINECONE_INDEX"))
openai.api_key = os.getenv("OPENAI_API_KEY")

def query_pinecone(question: str, namespace: str, top_k: int = 5):
    embed = openai.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )
    question_vector = embed.data[0].embedding

    result = index.query(
        vector=question_vector,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace
    )
    return result.matches