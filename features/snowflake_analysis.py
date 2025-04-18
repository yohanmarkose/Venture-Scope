import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd
import os
from dotenv import load_dotenv

class SnowflakeConnector:
    """
    A connector class for Snowflake operations related to market analysis and opportunity assessment.
    This class handles connections, table creation, data loading, and view generation.
    """
    
    def __init__(self, industry=None, size_category=None):
        """Initialize Snowflake connector with credentials from environment or config file"""
        load_dotenv()  # Load environment variables from .env file
        
        # Connection parameters from environment variables or config
        self.connection_params = {
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "database": os.getenv("SNOWFLAKE_DATABASE"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA"),
            "role": os.getenv("SNOWFLAKE_ROLE")
        }
        self.industry = industry
        self.size_category = size_category
        self.conn = None
    
    def connect(self):
        """Establish connection to Snowflake"""
        try:
            self.conn = snowflake.connector.connect(
                user=self.connection_params["user"],
                password=self.connection_params["password"],
                account=self.connection_params["account"],
                warehouse=self.connection_params["warehouse"],
                database=self.connection_params["database"],
                schema=self.connection_params["schema"],
                role=self.connection_params["role"]
            )
            print("Connected to Snowflake successfully!")
            return True
        except Exception as e:
            print(f"Error connecting to Snowflake: {e}")
            return False
    
    def disconnect(self):
        """Close the Snowflake connection"""
        if self.conn:
            self.conn.close()
            print("Disconnected from Snowflake.")
    
    def execute_query(self, query):
        """Execute a SQL query and return results"""
        if not self.conn:
            print("Not connected to Snowflake. Call connect() first.")
            return None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            
            # If query returns results, fetch them
            if cursor.description:
                result = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                cursor.close()
                return pd.DataFrame(result, columns=column_names)
            
            cursor.close()
            return True
        except Exception as e:
            print(f"Error executing query: {e}")
            print(f"Query: {query}")
            return None
    
    
    def get_company_data_by_industry(self, limit=20):
        """Get company data filtered by industry and optionally by size category"""

        where_clause = f"WHERE INDUSTRY LIKE '%{self.industry}%'"
        
        if self.size_category and self.size_category.lower() == "large":
            large_where_clause = where_clause + f" AND MARKET_CAP IS NOT NULL"
            large_table_name = "LARGE_COMPANY_DATA_FINAL"
            query_large = f"""
            SELECT *
            FROM opportunity_analysis.market_analysis.{large_table_name}
            {large_where_clause}
            ORDER BY MARKET_CAP DESC
            LIMIT {limit};
            """
            df = self.execute_query(query_large)
            if not df.empty and df.shape[0] > 4:
                return df
            
        table_name = "ENHANCED_COMPANIES"
        if self.size_category:
            where_clause += f" AND SIZE_CATAGORY = '{self.size_category}'"
        
        query_normal = f"""
        SELECT *
        FROM opportunity_analysis.market_analysis.{table_name}
        {where_clause}
        ORDER BY PERFORMANCE_SCORE DESC
        LIMIT {limit};
        """
        return self.execute_query(query_normal)

    def get_real_estate_data(self):
        query = f"""
        SELECT 
            GEO_NAME as state,
            AVG(VALUE) as avg_price_index,
            RANK() OVER (ORDER BY AVG(VALUE) DESC) as state_rank
        FROM 
            OPPORTUNITY_ANALYSIS.LOCATION_ANALYSIS.REAL_ESTATE_RATES_US
        WHERE 
            LEVEL = 'State'
            AND INDEX_TYPE = 'purchase-only' 
            AND SEASONALLY_ADJUSTED = FALSE 
            AND PROPERTY_CLASSIFICATION = 'traditional'
        GROUP BY 
            GEO_NAME
        ORDER BY 
            avg_price_index DESC;
        """
        return self.execute_query(query)

    
    def get_per_capita_income_data(self):
        query = f"""
        SELECT CITY, STATE, PER_CAPITA_INCOME
        FROM OPPORTUNITY_ANALYSIS.LOCATION_ANALYSIS.PER_CAPITA_INCOME_DETAIL
        ORDER BY STATE, CITY;
        """
        return self.execute_query(query)

    def get_top_performers_by_region(self, region, limit=20):
        """Get top performing companies in a specific region"""
        query = f"""
        SELECT *
        FROM opportunity_analysis.market_analysis.ENHANCED_COMPANIES
        WHERE REGION = '{region.lower()}'
        ORDER BY PERFORMANCE_SCORE DESC
        LIMIT {limit};
        """
        return self.execute_query(query)
    
    def get_statewise_count_by_industry(self, industry):
        """Get count of companies in each state filtered by industry"""
        query = f"""
        SELECT region, size_catagory as size_category, count(*) as count
        FROM enhanced_companies
        WHERE industry LIKE '%{industry}%'
        GROUP BY region, size_catagory
        """
        return self.execute_query(query)
    
    # def execute_setup(self):
    #     """Run all setup operations in sequence"""
    #     print("Setting up Snowflake environment...")
        
    #     if not self.connect():
    #         return False
        
    #     try:
    #         # # Create enhanced companies table
    #         # self.create_enhanced_companies_table()
            
    #         # # Create views by company size
    #         # self.create_company_size_views()
            
    #         # # Create tickers table and S3 integration
    #         # self.create_tickers_table_and_stage()
            
    #         print("Snowflake setup completed successfully!")
    #         return True
            
    #     except Exception as e:
    #         print(f"Error during Snowflake setup: {e}")
    #         return False
    #     finally:
    #         self.disconnect()

# Example usage
if __name__ == "__main__":
    # Create the connector
    sn_obj = SnowflakeConnector()
    
    # Run the full setup
    # snowflake.execute_setup()
    
    # Example: Get fintech companies
    sn_obj.connect()
    fintech_companies = sn_obj.get_company_data_by_industry(limit=5)
    if fintech_companies is not None:
        print(f"Found {len(fintech_companies)} fintech companies:")
        print(fintech_companies[['COMPANY_NAME', 'SIZE', 'WEBSITE', 'MARKET_CAP', 'PERFORMANCE_SCORE']])
    
    sn_obj.disconnect()