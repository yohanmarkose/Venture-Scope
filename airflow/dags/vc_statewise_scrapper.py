from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import time
import logging
from links_to_s3_push import upload_pdf_to_s3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.common.exceptions import TimeoutException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

default_args = {
    'owner': 'data_analyst',
    'depends_on_past': False,
    'start_date': datetime(2025, 4, 8),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'scrape_nvca_vc_statewise_pdf_link',
    default_args=default_args,
    description='Scrape SBA business structure information using Selenium',
    schedule_interval='@weekly',
    tags=["VC", "scraping", "markdown"],
    catchup=False
)

def initialize_selenium():
    """Initialize Selenium WebDriver with proper setup for Airflow container"""
    logger.info("Setting up Chrome options...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")
    
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    logger.info("Installing ChromeDriver using webdriver_manager...")
    try:
        # First attempt with standard Chrome
        service = Service(ChromeDriverManager().install())
        logger.info("Using standard ChromeDriver")
    except Exception as e:
        logger.warning(f"Failed to install standard ChromeDriver: {str(e)}")
        try:
            # Fallback to Chromium
            service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
            logger.info("Using Chromium ChromeDriver")
        except Exception as e:
            logger.error(f"Failed to install Chromium ChromeDriver: {str(e)}")
            raise
            
    logger.info("Initializing Chrome WebDriver...")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def scrape_pdf_links(ti,**kwargs):

    statename = kwargs['dag_run'].conf.get('statename', 'Massachusetts')
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Remote(
        command_executor="http://selenium-chrome:4444/wd/hub",
        options=chrome_options
    )

    url = f"https://nvca.org/document/{statename}-vc-state-data/"
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
    except TimeoutException:
        print("⚠️ Timed out waiting for page content to load.")
        driver.quit()
        return

    links = driver.find_elements(By.TAG_NAME, "a")
    pdf_links = [link.get_attribute("href") for link in links if link.get_attribute("href") and link.get_attribute("href").endswith(".pdf")]

    if pdf_links:
        print(f"📎 Found PDF link: {pdf_links[0]}")
    else:
        print("⚠️ No PDF links found on the page.")

    driver.quit()
    ti.xcom_push(key='pdf_link', value=pdf_links)


pdf_links = PythonOperator(
    task_id='pdf_link_collector',
    python_callable=scrape_pdf_links,
    dag=dag
)

pdf_s3_upload = PythonOperator(
    task_id='pdf_s3_upload',
    python_callable=upload_pdf_to_s3,
    dag=dag
)

# Define task dependencies
pdf_links >> pdf_s3_upload 