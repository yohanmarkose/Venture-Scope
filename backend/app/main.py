import io
import os, time, base64, asyncio, tempfile
from uuid import uuid4
from io import BytesIO
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.s3 import S3FileManager
from dotenv import load_dotenv
load_dotenv()

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

@app.get("/")
def read_root():
    return {"message": "Venture-Scope..."}

@app.post("/airflow_pdf_convert")
def process_pdf_mistral(uploaded_pdf: PdfInput):
    print("📥 Received request for PDF extraction")

    try:
        pdf_content = base64.b64decode(uploaded_pdf.file)
        pdf_stream = io.BytesIO(pdf_content)

        # Extract filename (for S3 destination path)
        file_name = uploaded_pdf.file_name or f"unknown_{uuid4()}.pdf"
        bucket_name = os.getenv("AWS_BUCKET_NAME", "default-bucket")
        base_path = "/".join(file_name.split("/")[:-1]) or "ocr-output"
        s3_obj = S3FileManager(bucket_name=bucket_name, base_prefix=base_path)
        file_name, result = pdf_mistralocr_converter(pdf_stream, base_path, s3_obj)

        print("✅ OCR conversion complete")

        return {
            "message": f"Data Scraped and stored in S3 \n Click the link to Download: https://{bucket_name}.s3.amazonaws.com/{file_name}",
            "file_name": file_name,
            "scraped_content": result
        }

    except Exception as e:
        print(f"❌ Error during PDF conversion: {str(e)}")
        return {
            "message": "Failed to process the PDF",
            "error": str(e)
        }
