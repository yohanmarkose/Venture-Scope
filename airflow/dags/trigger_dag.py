import requests
from requests.auth import HTTPBasicAuth

AIRFLOW_URL = "http://localhost:8080"
DAG_ID = "stock_valuation_to_snowflake"


# ocr_from_s3_selected_files_once
# payload = {
#     "conf": {
#         "base_path": "vc_reports",
#         "pdf_files": [
#             "Q1-2024-PitchBook-NVCA-Venture-Monitor.pdf",
#             "Q4-2024-PitchBook-NVCA-Venture-Monitor.pdf",
#             "Q3-2024-PitchBook-NVCA-Venture-Monitor.pdf",
#             "Q2-2024-PitchBook-NVCA-Venture-Monitor.pdf"
#         ]
#     }
# }


payload =   {
    "conf" :{
            "company": "Microsoft",
            "ticker": "MSFT"
            }
}


response = requests.post(
    f"{AIRFLOW_URL}/api/v1/dags/{DAG_ID}/dagRuns",
    json=payload,
    auth=HTTPBasicAuth("airflow", "airflow")
)

print("✅ Triggered!" if response.status_code == 200 else response.text)
