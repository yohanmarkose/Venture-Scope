import snowflake.connector
import logging

def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Set your connection parameters; update these with your actual credentials and environment details.
    conn_params = {
        'user': 'YOUR_USERNAME',
        'password': 'YOUR_PASSWORD',
        'account': 'YOUR_ACCOUNT',
        'warehouse': 'YOUR_WAREHOUSE',
        'database': 'YOUR_DATABASE',
        'schema': 'YOUR_SCHEMA',    # Note: not all queries use this default schema.
        'role': 'YOUR_ROLE'         # Optional: You can also include the role.
    }
    
    try:
        # Establish connection to Snowflake
        ctx = snowflake.connector.connect(
            user=conn_params['user'],
            password=conn_params['password'],
            account=conn_params['account'],
            warehouse=conn_params['warehouse'],
            database=conn_params['database'],
            schema=conn_params['schema'],
            role=conn_params['role']
        )
        cs = ctx.cursor()
        logging.info("Connected to Snowflake")
    except Exception as e:
        logging.error("Error connecting to Snowflake: %s", e)
        return

    try:
        # List of multi-statement queries to execute sequentially
        queries = [
            # Create Enhanced Companies Table
            """
            CREATE OR REPLACE TABLE opportunity_analysis.market_analysis.ENHANCED_COMPANIES AS
            WITH company_data AS (
                SELECT
                    ID,
                    NAME AS COMPANY_NAME,
                    INDUSTRY,
                    SIZE,
                    FOUNDED,
                    REGION,
                    COUNTRY,
                    LOCALITY,
                    WEBSITE,
                    LINKEDIN_URL,
                    2025 - FOUNDED AS company_age,
                    CASE
                        WHEN SIZE = '1-10' THEN 1
                        WHEN SIZE = '11-50' THEN 2
                        WHEN SIZE = '51-200' THEN 3
                        WHEN SIZE = '201-500' THEN 4
                        WHEN SIZE = '501-1000' THEN 5
                        WHEN SIZE = '1001-5000' THEN 6
                        WHEN SIZE = '5001-10000' THEN 7
                        WHEN SIZE = '10000+' THEN 8
                        ELSE 0
                    END AS size_score,
                    CASE
                        WHEN INDUSTRY LIKE '%tech%' OR INDUSTRY LIKE '%software%' THEN 1.5
                        WHEN INDUSTRY LIKE '%health%' OR INDUSTRY LIKE '%medical%' THEN 1.3
                        WHEN INDUSTRY LIKE '%finance%' OR INDUSTRY LIKE '%fintech%' THEN 1.2
                        WHEN INDUSTRY LIKE '%retail%' THEN 1.0
                        WHEN INDUSTRY LIKE '%manufacturing%' THEN 0.9
                        ELSE 1.0
                    END AS industry_growth_factor,
                    CASE
                        WHEN REGION IN ('california', 'new york', 'texas', 'massachusetts') THEN 1.2
                        WHEN REGION IN ('washington', 'colorado', 'florida', 'illinois') THEN 1.1
                        ELSE 1.0
                    END AS region_growth_factor
                FROM free_company_dataset.public.freecompanydataset
                WHERE 
                    COUNTRY = 'united states'
                    AND founded IS NOT NULL
                    AND industry IS NOT NULL
                    AND website IS NOT NULL
                    AND region IS NOT NULL
            ),
            performance_calculated AS (
                SELECT
                    *,
                    CASE
                        WHEN company_age <= 3 THEN 70
                        WHEN company_age > 3 AND company_age <= 10 THEN 85
                        WHEN company_age > 10 AND company_age <= 20 THEN 80
                        ELSE 75
                    END
                    * (0.8 + (size_score * 0.05))
                    * industry_growth_factor
                    * region_growth_factor
                    AS raw_performance_score
                FROM company_data
            )
            SELECT
                ID,
                COMPANY_NAME,
                INDUSTRY,
                SIZE,
                FOUNDED,
                REGION,
                COUNTRY,
                LOCALITY,
                WEBSITE,
                LINKEDIN_URL,
                company_age,
                CASE
                    WHEN SIZE IN ('1001-5000', '5001-10000', '10001+') THEN 'large'
                    WHEN SIZE IN ('51-200', '201-500', '501-1000') THEN 'medium'
                    WHEN SIZE IN ('1-10', '11-50') THEN 'small'
                END AS size_catagory,
                CASE
                    WHEN raw_performance_score >= 130 THEN 'High Performer'
                    WHEN raw_performance_score >= 100 AND raw_performance_score < 130 THEN 'Strong Performer'
                    WHEN raw_performance_score >= 80 AND raw_performance_score < 100 THEN 'Steady Performer'
                    WHEN raw_performance_score >= 60 AND raw_performance_score < 80 THEN 'Developing'
                    ELSE 'Emerging'
                END AS performance_category,
                ROUND(raw_performance_score, 2) AS performance_score
            FROM performance_calculated
            ORDER BY raw_performance_score DESC;
            """,
            # Small Companies View
            """
            CREATE OR REPLACE VIEW opportunity_Analysis.market_analysis.small_companies AS
            SELECT
              ID,
              INDUSTRY,
              COMPANY_NAME,
              SIZE,
              FOUNDED,
              REGION,
              COUNTRY,
              LOCALITY,
              WEBSITE,
              LINKEDIN_URL,
              COMPANY_AGE,
              SIZE_CATAGORY,
              PERFORMANCE_CATEGORY,
              PERFORMANCE_SCORE
            FROM 
                opportunity_analysis.market_analysis.enhanced_companies
            WHERE
                SIZE_CATAGORY = 'small';
            """,
            # Medium Companies View
            """
            CREATE OR REPLACE VIEW opportunity_Analysis.market_analysis.medium_companies AS
            SELECT
              ID,
              INDUSTRY,
              COMPANY_NAME,
              SIZE,
              FOUNDED,
              REGION,
              COUNTRY,
              LOCALITY,
              WEBSITE,
              LINKEDIN_URL,
              COMPANY_AGE,
              SIZE_CATAGORY,
              PERFORMANCE_CATEGORY,
              PERFORMANCE_SCORE
            FROM 
                opportunity_analysis.market_analysis.enhanced_companies
            WHERE
                SIZE_CATAGORY = 'medium';
            """,
            # Large Companies View
            """
            CREATE OR REPLACE VIEW opportunity_Analysis.market_analysis.large_companies AS
            SELECT
              ID,
              INDUSTRY,
              COMPANY_NAME,
              SIZE,
              FOUNDED,
              REGION,
              COUNTRY,
              LOCALITY,
              WEBSITE,
              LINKEDIN_URL,
              COMPANY_AGE,
              SIZE_CATAGORY,
              PERFORMANCE_CATEGORY,
              PERFORMANCE_SCORE
            FROM 
                opportunity_analysis.market_analysis.enhanced_companies
            WHERE
                SIZE_CATAGORY = 'large';
            """,
            # Create TICKERS table
            """
            CREATE OR REPLACE TABLE TICKERS (
                TICKER VARCHAR,
                COMPANY_NAME VARCHAR
            );
            """,
            # Create stage for S3 bucket
            """
            CREATE OR REPLACE STAGE my_s3_stage
                URL = 's3://mdcontents/'
                CREDENTIALS = (AWS_KEY_ID = 'AKIA4SZHNTVUXP4OX3VV' 
                               AWS_SECRET_KEY = 'sE6Bupmmbmxo5boOvSQedcNJVsFdsstQ0FO151mX');
            """,
            # Create file format for CSV
            """
            CREATE OR REPLACE FILE FORMAT my_csv_format
            TYPE = CSV
            SKIP_HEADER = 1
            FIELD_OPTIONALLY_ENCLOSED_BY='"'
            NULL_IF = ('', 'NULL');
            """,
            # Load tickers from S3
            """
            COPY INTO tickers
            FROM @my_s3_stage/ticker/us_listed_tickers.csv
            FILE_FORMAT = my_csv_format;
            """,
            # Create FUZZY_SCORE function
            """
            CREATE OR REPLACE FUNCTION FUZZY_SCORE(NAME_A STRING, NAME_B STRING)
            RETURNS FLOAT
            LANGUAGE PYTHON
            RUNTIME_VERSION = '3.8'
            PACKAGES = ('rapidfuzz')
            HANDLER = 'handler_func'
            AS
            $$
            from rapidfuzz import fuzz
            def handler_func(str1, str2):
                return fuzz.partial_ratio(str1, str2)  
            $$;
            """,
            # Set role and warehouse for large companies with ticker processing
            """
            use role accountadmin;
            ALTER WAREHOUSE dbt_wh SET WAREHOUSE_SIZE = LARGE;
            use role fin_role;
            use warehouse dbt_wh;
            use schema market_analysis;
            """,
            # Create table with large companies and ticker matching
            """
            CREATE OR REPLACE TABLE opportunity_analysis.market_analysis.large_companies_with_ticker AS
            WITH fuzzy_matches AS (
                SELECT
                    M.COMPANY_NAME,
                    T.COMPANY_NAME AS TICKER_COMPANY_NAME,
                    T.TICKER,
                    FUZZY_SCORE(LOWER(M.COMPANY_NAME), LOWER(T.COMPANY_NAME)) AS SCORE,
                    SPLIT_PART(TRIM(LOWER(M.COMPANY_NAME)), ' ', 1) AS FIRST_WORD,
                    ROW_NUMBER() OVER (
                        PARTITION BY M.COMPANY_NAME 
                        ORDER BY FUZZY_SCORE(LOWER(M.COMPANY_NAME), LOWER(T.COMPANY_NAME)) DESC
                    ) AS rn
                FROM opportunity_analysis.market_analysis.large_companies M
                CROSS JOIN TICKERS T
                WHERE 
                    FUZZY_SCORE(LOWER(M.COMPANY_NAME), LOWER(T.COMPANY_NAME)) >= 85
                    AND POSITION(SPLIT_PART(TRIM(LOWER(M.COMPANY_NAME)), ' ', 1) IN LOWER(T.COMPANY_NAME)) > 0
            )
            SELECT
                M.*,
                fm.TICKER AS T_SYMBOL
            FROM opportunity_analysis.market_analysis.large_companies M
            LEFT JOIN fuzzy_matches fm
                ON M.COMPANY_NAME = fm.COMPANY_NAME AND fm.rn = 1
            ORDER BY M.COMPANY_NAME;
            """,
            # Reset warehouse size and switch roles/schemas back
            """
            use role accountadmin;
            ALTER WAREHOUSE dbt_wh SET WAREHOUSE_SIZE = 'X-small';
            use role fin_role;
            use warehouse dbt_wh;
            use schema market_analysis;
            """
        ]
        
        # Execute each query one by one
        for query in queries:
            query_preview = query.strip().replace("\n", " ")[:100]  # preview first 100 characters
            logging.info("Executing query: %s", query_preview)
            cs.execute(query)
            logging.info("Query executed successfully.\n")
        
        # Optionally, commit changes if needed (DDL is auto-committed, but DML would require a commit)
        # ctx.commit()

    except Exception as e:
        logging.error("Error executing queries: %s", e)
    finally:
        cs.close()
        ctx.close()
        logging.info("Connection to Snowflake closed.")

if __name__ == '__main__':
    main()