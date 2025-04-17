import base64
import ftplib
import requests
import pandas as pd
from io import StringIO, BytesIO

def fetch_all_us_listed_companies(**kwargs):
    urls = {
        "nasdaqlisted": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
        "otherlisted": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
    }

    dfs = []
    for name, url in urls.items():
        response = requests.get(url)
        content = response.content.decode("utf-8")
        df = pd.read_csv(StringIO(content), sep="|")[:-1]

        if "Symbol" in df.columns:
            df.rename(columns={'Symbol': 'ticker', 'Security Name': 'company_name'}, inplace=True)
        elif "ACT Symbol" in df.columns:
            df.rename(columns={'ACT Symbol': 'ticker', 'Security Name': 'company_name'}, inplace=True)

        df = df[df['ticker'].notna() & (~df['ticker'].str.contains(r'\$', na=False))]
        dfs.append(df[['ticker', 'company_name']])

    final_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    csv_buffer = BytesIO()
    final_df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    csv_base64 = base64.b64encode(csv_buffer.getvalue()).decode("utf-8")
    kwargs['ti'].xcom_push(key='ticker_csv_b64', value=csv_base64)