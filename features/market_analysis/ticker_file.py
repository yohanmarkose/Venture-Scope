import ftplib
import pandas as pd
from io import StringIO

def fetch_all_us_listed_companies() -> pd.DataFrame:
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

        # Standardize column names
        if 'Symbol' in df.columns:
            df.rename(columns={'Symbol': 'ticker', 'Security Name': 'company_name'}, inplace=True)
        elif 'ACT Symbol' in df.columns:
            df.rename(columns={'ACT Symbol': 'ticker', 'Security Name': 'company_name'}, inplace=True)

        # Keep only rows with non-empty ticker
        df = df[df['ticker'].notna() & (df['ticker'].str.strip() != '') & (~df['ticker'].str.contains('\\$', na=False))]

        dfs.append(df[['ticker', 'company_name']])

    ftp.quit()

    combined_df = pd.concat(dfs, ignore_index=True).drop_duplicates()
    return combined_df

if __name__ == "__main__":
    df = fetch_all_us_listed_companies()
    print(df.head())
    # Save to CSV if needed
    df.to_csv('us_listed_tickers.csv', index=False)
    # save to s3