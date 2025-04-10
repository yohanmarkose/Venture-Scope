import base64
import io
import requests
from services.s3 import S3FileManager
from airflow.models import TaskInstance
from airflow.models import Variable

AWS_BUCKET_NAME = Variable.get("AWS_BUCKET_NAME")
FASTAPI_URL = Variable.get("FASTAPI_URL")

def pdf_mistralocr_converter(ti: TaskInstance, **kwargs):
    filename_data = ti.xcom_pull(task_ids=kwargs['source_task_id'], key='raw_pdf_s3_link')

    if not filename_data or not isinstance(filename_data, list) or not filename_data[0].get('year'):
        raise ValueError(f"Invalid or missing XCom data for task {kwargs['source_task_id']}")

    filename = filename_data[0]['filename']
    year = filename_data[0]['year']
    quarter = filename_data[0]['quarter']

    base_path = f"nvidia/{year}/{quarter}"

    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
    files = list({file for file in s3_obj.list_files() if file.endswith('.pdf')})
    print(files) 
    for file in files:
        pdf_file = s3_obj.load_s3_pdf(file)
        pdf_bytes = io.BytesIO(pdf_file)
        base64_pdf = base64.b64encode(pdf_bytes.getvalue()).decode('utf-8')
        response = requests.post(f"{FASTAPI_URL}/upload_pdf", json={"file": base64_pdf, "file_name": file, "parser": 'mistral'})
    try:
        if response.status_code == 200:
            print(f"Mistral OCR processing for {filename} triggered...!")
            data = response.json()
            file_name = "/".join(filename.split('/')[:-1]) + "/mistral/extracted_data.md"
            print(file_name)
            scraped_content = data["scraped_content"]
            s3_obj.upload_file(s3_obj.bucket_name, file_name, scraped_content.encode('utf-8'))
    except Exception as e:
        print(f"Error during docling processing for {filename}")