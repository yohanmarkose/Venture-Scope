from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def scrape_sba_markdown():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Remote(
        command_executor="http://selenium-chrome:4444/wd/hub",
        options=chrome_options
    )

    url = "https://www.sba.gov/business-guide/launch-your-business/choose-business-structure"
    driver.get(url)
    time.sleep(3)  # Let content load

    print("# 📄 SBA Business Structures\n")

    content_blocks = driver.find_elements(By.CSS_SELECTOR, "div.node__content > *")
    markdown_output = ""
    html_tables = []

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "main"))
        )
    except TimeoutException:
        print("⚠️ Timed out waiting for page content to load.")
        driver.quit()
        return

    markdown_output = "# 📄 SBA Business Structures\n"
    html_tables = []

    elements = driver.find_elements(By.XPATH, "//main//*[self::h2 or self::h3 or self::p or self::ul or self::table]")

    for elem in elements:
        tag = elem.tag_name
        text = elem.text.strip()

        if tag in ["h2", "h3"] and text:
            markdown_output += f"\n## {text}\n"
        elif tag == "p" and text:
            markdown_output += f"{text}\n\n"
        elif tag == "ul":
            items = elem.find_elements(By.TAG_NAME, "li")
            for li in items:
                markdown_output += f"- {li.text.strip()}\n"
            markdown_output += "\n"
        elif tag == "table":
            html = elem.get_attribute("outerHTML")
            html_tables.append(html)
            markdown_output += "\n**[Table found — see raw HTML below]**\n"

    print(markdown_output)

    if html_tables:
        print("\n\n## 📊 Raw Table HTML(s):\n")
        for i, table in enumerate(html_tables, 1):
            print(f"\n---\n### Table {i}\n{table}\n")


    driver.quit()

default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 1, 1),
}

with DAG(
    dag_id="sba_scrape_markdown_dag_v1",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    tags=["sba", "scraping", "markdown"]
) as dag:

    scrape_task = PythonOperator(
        task_id="scrape_sba_to_markdown_v1",
        python_callable=scrape_sba_markdown
    )

    scrape_task
