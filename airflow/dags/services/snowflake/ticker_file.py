import base64
import ftplib
import pandas as pd
from io import StringIO, BytesIO

def fetch_all_us_listed_companies(**kwargs):
    ftp = ftplib.FTP('ftp.nasdaqtrader.com')
    ftp.login()
    ftp.encoding = 'utf-8'
    ftp.cwd('SymbolDirectory')

    files = ["nasdaqlisted.txt", "otherlisted.txt"]
    dfs = []

    for file in files:
        lines = []
        ftp.retrlines(f"RETR {file}", lines.append)
        content = "\n".join(lines)
        df = pd.read_csv(StringIO(content), sep="|")
        df = df[:-1]  # remove footer row

        if 'Symbol' in df.columns:
            df.rename(columns={'Symbol': 'ticker', 'Security Name': 'company_name'}, inplace=True)
        elif 'ACT Symbol' in df.columns:
            df.rename(columns={'ACT Symbol': 'ticker', 'Security Name': 'company_name'}, inplace=True)

        df = df[df['ticker'].notna() & (~df['ticker'].str.contains('\\$', na=False))]
        dfs.append(df[['ticker', 'company_name']])

    ftp.quit()
    combined_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    # Convert DataFrame to CSV BytesIO
    csv_buffer = BytesIO()
    csv_bytes = csv_buffer.getvalue()
    csv_base64 = base64.b64encode(csv_bytes).decode("utf-8")

    # Push to XCom
    kwargs['ti'].xcom_push(key='ticker_csv_b64', value=csv_base64)