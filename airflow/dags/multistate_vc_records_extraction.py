from airflow import DAG
from airflow.decorators import dag, task, task_group
from airflow.models import Variable
from airflow.utils.dates import days_ago
from pathlib import Path
import io
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from services.links_to_s3_push import upload_pdf_to_s3
from services.s3 import S3FileManager
from services.mistral_orc_processing import pdf_mistralocr_converter


@dag(
    dag_id='scrape_nvca_vc_statewise_grouped',
    default_args={
        'owner': 'data_team',
        'start_date': days_ago(1),
        'retries': 1,
    },
    schedule_interval='@weekly',
    catchup=False,
    tags=['vc_scraper', 'grouped'],
    max_active_runs=1,
    max_active_tasks=3
)
def vc_state_pipeline():

    @task
    def get_states():
        # You can also fetch this from Airflow Variables or a config file
        return ["California", "Texas", "Massachusetts"]

    @task_group
    def process_state(state: str):
        @task
        def fetch_pdf_link(state: str) -> str:
            print(f"🌐 Scraping NVCA PDF link for: {state}")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            driver = webdriver.Remote(
                command_executor="http://selenium-chrome:4444/wd/hub",
                options=chrome_options
            )

            url = f"https://nvca.org/document/{state.lower()}-vc-state-data/"
            driver.get(url)

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "a"))
                )
                links = driver.find_elements(By.TAG_NAME, "a")
                pdf_links = [
                    l.get_attribute("href") for l in links
                    if l.get_attribute("href") and l.get_attribute("href").endswith(".pdf")
                ]
            except TimeoutException:
                driver.quit()
                raise Exception(f"⏳ Timed out waiting for {state} PDF link")

            driver.quit()

            if not pdf_links:
                raise Exception(f"❌ No PDF links found for {state}")
            
            print(f"📎 Found PDF for {state}: {pdf_links[0]}")
            return pdf_links[0]

        @task
        def upload_to_s3(pdf_url: str, state: str) -> str:
            print(f"⬆️ Uploading PDF to S3 for: {state}")
            return upload_pdf_to_s3(pdf_url, state)

        @task
        def run_mistral_ocr(s3_path: str, state: str) -> str:
            print(f"🔍 Running Mistral OCR for: {state}")
            AWS_BUCKET_NAME = Variable.get("AWS_BUCKET_NAME")
            s3_obj = S3FileManager(AWS_BUCKET_NAME, s3_path)
            pdf_file = s3_obj.load_s3_pdf(s3_path)
            pdf_stream = io.BytesIO(pdf_file)
            output_path = f"{Path(s3_path).parent}/mistral"
            file_name, content = pdf_mistralocr_converter(pdf_stream, output_path, s3_obj)
            print(f"✅ Markdown saved to: {file_name}")
            return file_name

        # Wire up the tasks inside the group
        run_mistral_ocr(
            s3_path=upload_to_s3(
                pdf_url=fetch_pdf_link(state),
                state=state
            ),
            state=state
        )

    # Main DAG logic
    states = get_states()
    process_state.expand(state=states)


vc_state_pipeline()