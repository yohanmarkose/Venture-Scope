import asyncio
import os
from dotenv import load_dotenv
from agents import Runner,handoff
from agents_mcp import Agent, RunnerContext
from openai import OpenAI
from pydantic import BaseModel
from agents import set_tracing_export_api_key, RunContextWrapper
load_dotenv()

api_key=os.getenv("OPENAI_API_KEY")
set_tracing_export_api_key(api_key=api_key)


mcp_config_path = "mcp_agent_config.yaml"
context = RunnerContext(mcp_config_path=mcp_config_path)

class CityData(BaseModel):
   places: str
   
async def process_citydata(ctx: RunContextWrapper, input_data: CityData):
   print(f"citydata: {input_data.places}")
   

businessagent = Agent(
        name = "Business Proposal Agent",
        instructions = """You are a business consultant. 
                            You are given an industry, product, location/city, size of the company and Unique Selling Proposition. 
                            You need to give a complete proposal for the business. 
                            The proposal should include the following: 
                            1. Business Plan 
                            2. Market Research 
                            3. Financial Projections 
                            4. Marketing Strategy 
                            5. Operational Plan 
                            6. Competitors in region 
                            7. Management Team 
                            8. Funding Requirements""",
    )

locationagent = Agent(
        name = 'Location Agent',
        instructions = """Based on the business proposal, you need to find the best location for the business. 
                            Include competitors in this said location to support your decisions.
                            The output strictly has to be JSON formatted. 
                            You need to provide a list of places that are suitable for the business. 
                            The list should include the following: 1. City 2. State 3. Country 4. Population 5. Cost of Living 6. Business Environment 7. Infrastructure. 
                            Based on the locations identified, you need to provide a list of competitors in the region. The list should include the following: 1. Name 2. Industry 3. Location 4. Size 5. Revenue 6. Market Share""",
        # handoffs=[handoff(agent=cityagent, on_handoff=process_citydata, input_type=CityData)]
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
        "size": input("What is the size of business (Ex. Startup, SME, MNC)? "),
        "usp": input("What is your Unique Selling Proposition? ")
    }

    raw_info = "\n".join(f"{k}: {v}" for k, v in business_info.items())

    first_result = await Runner.run(
        businessagent,raw_info
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