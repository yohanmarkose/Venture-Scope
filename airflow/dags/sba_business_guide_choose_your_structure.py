from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

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
    'sba_business_structure_scraper_selenium',
    default_args=default_args,
    description='Scrape SBA business structure information using Selenium',
    schedule_interval='@weekly',
    tags=["vc_reports", "scraping", "markdown",'venture-scope'],
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
    
    # Required for running in Docker
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")
    
    # Fix for running in Docker container
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    logger.info("Installing ChromeDriver using webdriver_manager...")
    # Use webdriver_manager to handle driver installation
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

def scrape_business_structure_data():
    """Scrape SBA website for business structure information using Selenium"""
    url = "https://www.sba.gov/business-guide/launch-your-business/choose-business-structure"
    output_dir = "/opt/airflow/data/sba"
    output_file = f"{output_dir}/business_structures_{datetime.now().strftime('%Y%m%d')}.md"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Initializing Selenium to scrape {url}")
    driver = None
    
    try:
        driver = initialize_selenium()
        
        logger.info(f"Navigating to {url}")
        driver.get(url)
        
        # Wait for the main content to load
        logger.info("Waiting for page content to load...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Allow additional time for dynamic content to load
        time.sleep(3)
        
        # Get the main title
        logger.info("Extracting main title...")
        main_title = driver.find_element(By.TAG_NAME, "h1").text
        
        # Begin building markdown content
        markdown_content = f"# {main_title}\n\n"
        markdown_content += f"*Scraped from {url} on {datetime.now().strftime('%Y-%m-%d')}*\n\n"
        
        # Get the introduction paragraph(s)
        logger.info("Extracting introduction paragraphs...")
        intro_section = driver.find_element(By.TAG_NAME, "main")
        intro_paragraphs = intro_section.find_elements(By.TAG_NAME, "p")
        
        for para in intro_paragraphs[:2]:  # First couple paragraphs are usually intro
            markdown_content += f"{para.text}\n\n"
        
        # Find all business structure sections (typically h2 headers)
        logger.info("Finding business structure sections...")
        business_structures = driver.find_elements(By.TAG_NAME, "h2")
        
        # Process each business structure section
        for structure in business_structures:
            structure_name = structure.text
            
            # Skip non-business structure headers
            if not any(keyword in structure_name.lower() for keyword in 
                      ["proprietorship", "partnership", "corporation", "llc", "cooperative", "structure"]):
                continue
                
            logger.info(f"Processing structure: {structure_name}")
            markdown_content += f"## {structure_name}\n\n"
            
            # Get the next sibling elements until the next h2
            current = structure
            while True:
                try:
                    current = driver.execute_script("""
                        return arguments[0].nextElementSibling;
                    """, current)
                    
                    if current is None:
                        break
                        
                    # Check if we've reached the next h2
                    if current.tag_name == "h2":
                        break
                        
                    # Process based on element type
                    if current.tag_name == "p":
                        markdown_content += f"{current.text}\n\n"
                    elif current.tag_name == "ul":
                        list_items = current.find_elements(By.TAG_NAME, "li")
                        for item in list_items:
                            markdown_content += f"* {item.text}\n"
                        markdown_content += "\n"
                    
                except Exception as e:
                    logger.warning(f"Error processing element: {str(e)}")
                    break
        
        # Look for any comparison tables
        logger.info("Looking for comparison tables...")
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            markdown_content += "## Comparison Table\n\n"
            
            # Get headers
            headers = table.find_elements(By.TAG_NAME, "th")
            header_row = "|"
            separator_row = "|"
            
            for header in headers:
                header_row += f" {header.text} |"
                separator_row += " --- |"
            
            markdown_content += f"{header_row}\n{separator_row}\n"
            
            # Get rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            for row in rows[1:]:  # Skip header row
                cells = row.find_elements(By.TAG_NAME, "td")
                row_content = "|"
                for cell in cells:
                    row_content += f" {cell.text} |"
                markdown_content += f"{row_content}\n"
            
            markdown_content += "\n"
        
        # Save to markdown file
        logger.info(f"Saving markdown content to {output_file}")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        logger.info(f"Successfully scraped SBA business structure data to {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error scraping SBA website: {str(e)}")
        raise
    finally:
        if driver:
            logger.info("Closing WebDriver")
            driver.quit()

def validate_markdown_file(**context):
    """Validate that the markdown file was created and has content"""
    file_path = context['ti'].xcom_pull(task_ids='scrape_sba_business_structures')
    
    if not os.path.exists(file_path):
        raise ValueError(f"Output file {file_path} does not exist")
        
    file_size = os.path.getsize(file_path)
    if file_size < 100:  # Arbitrary minimum size
        raise ValueError(f"Output file {file_path} is too small ({file_size} bytes)")
        
    logger.info(f"Validation passed: {file_path} exists with {file_size} bytes")
    
    # Print first few lines of the file for verification
    with open(file_path, 'r', encoding='utf-8') as f:
        preview = f.read(500)
        logger.info(f"File preview: \n{preview}...")
    
    return True

scrape_task = PythonOperator(
    task_id='scrape_sba_business_structures',
    python_callable=scrape_business_structure_data,
    dag=dag
)

validate_task = PythonOperator(
    task_id='validate_markdown_output',
    python_callable=validate_markdown_file,
    provide_context=True,
    dag=dag
)

# Define task dependencies
scrape_task >> validate_task