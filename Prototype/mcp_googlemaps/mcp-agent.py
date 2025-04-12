import asyncio
import os
from dotenv import load_dotenv
from agents import Runner, handoff, set_tracing_export_api_key, RunContextWrapper, enable_verbose_stdout_logging
from agents_mcp import Agent, RunnerContext
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

enable_verbose_stdout_logging()

mcp_config_path = "mcp_agent.config.yaml"
context = RunnerContext(mcp_config_path=mcp_config_path)

class CityData(BaseModel):
   places: str
   
async def process_citydata(ctx: RunContextWrapper, input_data: CityData):
   print(f"citydata: {input_data.places}")
   

businessagent = Agent(
        name = "Business Proposal Agent",
        instructions = """You are an elite location strategy business consultant with 20+ years of experience in site selection, competitive analysis, and market entry planning exclusively within the United States. 
                            Your analyses have guided Fortune 500 companies and high-growth startups to identify optimal locations that maximize profitability and market penetration. 
                            You are given an industry, product, preffered (city, state), budget range, size of the company and Unique Selling Proposition. 
                            Taking into account the information you have, generate a detailed report that includes the following:
                            1. Industry Overview: Provide a brief overview of the industry, including current trends and growth potential.
                            2. Market Analysis: Analyze the market potential for the product in the specified location, including target demographics and demand.
                            3. Location Suitability: Evaluate the suitability of the areas in the preferred cities for the business, considering factors such as cost of living, infrastructure, and local regulations.
                            4. Competitive Landscape: Identify key competitors in the area and analyze their strengths and weaknesses.
                            5. Financial Projections: Offer financial projections, including estimated costs, revenues, and return on investment.
                            6. Risk Assessment: Identify potential risks and challenges associated with the business in the specified location, along with mitigation strategies.
                            7. Recommendations: Provide actionable recommendations for the business, including potential locations, marketing strategies, and partnerships.
                            8. Conclusion: Summarize the key findings and recommendations in a clear and concise manner.
                            """,
    )

locationagent: Agent = Agent(
        name = 'Location Agent',
        instructions = """You are an assitant able to interact with Google Maps API integration with MCP. Use the tools and based on the business proposal, you need to find the top 3 locations for the business. 
                            Include competitors in these said location to support your decisions.
                            The output strictly has to be JSON formatted. 
                            You need to provide a list of places that are suitable for the business in and around the mentioned cities. 
                                The list should strictly include the following: 
                                    1. Area
                                    2. City, State
                                    3. Population Density (Low, Medium, High)
                                    4. Cost of Living (Low, Medium, High)
                                    5. Business Climate
                                    6. Quality of Life
                                    7. Infrastructure
                                    8. Suitability Score (1-10)
                                    9. Risk Score (1-10)
                                    10. Advantages [List] (in detail)
                                    11. Challenges [List] (in detail)
                                    12. Competitors 
                            For each locations identified, you need to find the list of top 5 competitors in the area. 
                                The list should strictly include the following: 
                                    1. Name 
                                    2. Industry 
                                    3. Address 
                                    4. Size 
                                    5. Revenue 
                                    6. Market Share
                                    7. Unique Selling Proposition
                                    8. Growth Score (1-10)
                                    9. Customer Satisfaction Score (1-10)
                                    10. Reviews [List]
                                    11. Rating""",
        # tools = ["maps_search_places", "maps_place_details"],
        # mcp_servers=["google-maps"],
    )

synthesizer_agent = Agent(
    name="synthesizer_agent",
    instructions="You take the input and then output one JSON object (locations, competitors) without the ticks to pass it to our API for processing. Strictly use JSON format for competitors. Strictly use JSON format for the ideal locations.",
)

async def main():
    
    business_info = {
        "industry": input("What is the industry for your business? "),
        "product": input("What is going to be your product? "),
        "location/city": input("What city is ideal for you? "),
        "budget": input("What is your budget range? (Ex. 1000-5000) "),
        "size": input("What is the size of business (Ex. Startup, SME, MNC)? "),
        "unique_selling_proposition": input("What is your Unique Selling Proposition? ")
    }

    raw_info = "\n".join(f"{k}: {v}" for k, v in business_info.items())
    
    context = RunnerContext()

    first_result = await Runner.run(
        businessagent,raw_info, 
    )

    # print(first_result.final_output)
    
    second_result = await Runner.run(
        locationagent, first_result.final_output, context=context
    )

    # print(second_result.final_output)

    third_result = await Runner.run(
        synthesizer_agent, second_result.final_output
    )

    print(third_result.final_output)


if __name__ == "__main__":
    asyncio.run(main())