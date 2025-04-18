from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from datetime import datetime

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
}

with DAG(
    dag_id='custom_usretailestate_raw_data_snowflake_v1',
    default_args=default_args,
    tags=['snowflake','dataload','location_analysis','usretailestate','marketplace','venture-scope'],
    description='Loads or reloads dataset from Snowflake Marketplace for US Real Estate',
    schedule_interval='0 0 1 1,4,7,10 *',
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    # Start task
    start = EmptyOperator(task_id='start')

    # Grouping Snowflake tasks together
    with TaskGroup("snowflake_tasks", tooltip="Load Marketplace Data into Snowflake") as snowflake_location_analysis_group:

        create_per_capita_income_table = SnowflakeOperator(
            task_id='create_or_replace_income_table',
            snowflake_conn_id='snowflake_default',
            sql="""
                USE ROLE FIN_ROLE;
                USE WAREHOUSE DBT_WH;
                CREATE SCHEMA IF NOT EXISTS OPPORTUNITY_ANALYSIS.LOCATION_ANALYSIS;

                CREATE OR REPLACE TABLE OPPORTUNITY_ANALYSIS.LOCATION_ANALYSIS.PER_CAPITA_INCOME AS
                SELECT
                    addr.city,
                    addr.state,
                    geo.geo_name AS zip_code,
                    ROUND(agi.value / NULLIF(pop.value, 0), 0) AS per_capita_income
                FROM US_REAL_ESTATE.CYBERSYN.IRS_INDIVIDUAL_INCOME_TIMESERIES agi
                JOIN US_REAL_ESTATE.CYBERSYN.IRS_INDIVIDUAL_INCOME_TIMESERIES pop
                    ON agi.geo_id = pop.geo_id
                    AND agi.date = pop.date
                    AND pop.variable_name = 'Number of individuals, AGI bin: Total'
                JOIN US_REAL_ESTATE.CYBERSYN.GEOGRAPHY_INDEX geo 
                    ON agi.geo_id = geo.geo_id
                JOIN US_REAL_ESTATE.CYBERSYN.US_ADDRESSES addr 
                    ON geo.geo_name = addr.zip
                WHERE agi.variable_name = 'Adjusted gross income (AGI), AGI bin: Total'
                  AND geo.level = 'CensusZipCodeTabulationArea'
                  AND pop.value > 10000
                GROUP BY addr.city, addr.state, geo.geo_name, agi.value, pop.value
                ORDER BY per_capita_income DESC;
            """
        )

        create_per_capita_income_detail_table = SnowflakeOperator(
            task_id='create_income_detail_table',
            snowflake_conn_id='snowflake_default',
            sql="""
                USE ROLE FIN_ROLE;
                USE WAREHOUSE DBT_WH;
                CREATE SCHEMA IF NOT EXISTS OPPORTUNITY_ANALYSIS.LOCATION_ANALYSIS;

                CREATE OR REPLACE TABLE OPPORTUNITY_ANALYSIS.LOCATION_ANALYSIS.PER_CAPITA_INCOME_DETAIL AS
                SELECT
                    addr.city,
                    addr.state,
                    geo.geo_name AS zip_code,
                    ROUND(agi.value / NULLIF(pop.value, 0), 0) AS per_capita_income
                FROM US_REAL_ESTATE.CYBERSYN.IRS_INDIVIDUAL_INCOME_TIMESERIES agi
                JOIN US_REAL_ESTATE.CYBERSYN.IRS_INDIVIDUAL_INCOME_TIMESERIES pop
                    ON agi.geo_id = pop.geo_id
                    AND agi.date = pop.date
                    AND pop.variable_name = 'Number of individuals, AGI bin: Total'
                JOIN US_REAL_ESTATE.CYBERSYN.GEOGRAPHY_INDEX geo 
                    ON agi.geo_id = geo.geo_id
                JOIN US_REAL_ESTATE.CYBERSYN.US_ADDRESSES addr 
                    ON geo.geo_name = addr.zip
                WHERE agi.variable_name = 'Adjusted gross income (AGI), AGI bin: Total'
                  AND geo.level = 'CensusZipCodeTabulationArea'
                  AND pop.value > 10000
                GROUP BY addr.city, addr.state, geo.geo_name, agi.value, pop.value
                ORDER BY per_capita_income DESC;
            """
        )

        real_estate_rates_us_detail_table = SnowflakeOperator(
            task_id='real_estate_rates_us_detail_table',
            snowflake_conn_id='snowflake_default',
            sql="""
                USE ROLE FIN_ROLE;
                USE WAREHOUSE DBT_WH;
                CREATE SCHEMA IF NOT EXISTS OPPORTUNITY_ANALYSIS.LOCATION_ANALYSIS;

                CREATE OR REPLACE TABLE OPPORTUNITY_ANALYSIS.LOCATION_ANALYSIS.REAL_ESTATE_RATES_US AS
                SELECT
                    fhpt.variable,
                    fhpt.geo_id,
                    fhpt.value,
                    fhpt.unit AS value_unit,
                    fhpt.variable_name,
                    fhpt.date,
                    gi.geo_name,
                    gi.level,
                    fhpa.index_type,
                    fhpa.seasonally_adjusted,
                    fhpa.property_classification,
                    fhpa.frequency,
                    fhpa.unit AS attribute_unit
                FROM US_REAL_ESTATE.CYBERSYN.fhfa_house_price_timeseries AS fhpt
                JOIN US_REAL_ESTATE.CYBERSYN.geography_index AS gi
                    ON fhpt.geo_id = gi.geo_id
                JOIN US_REAL_ESTATE.CYBERSYN.fhfa_house_price_attributes AS fhpa
                    ON fhpt.variable = fhpa.variable;
            """
        )

    # End task
    end = EmptyOperator(task_id='end')

    # DAG flow
    start >> snowflake_location_analysis_group >> end