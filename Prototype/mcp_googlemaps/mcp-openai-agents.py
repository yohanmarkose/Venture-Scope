import asyncio
import shutil, os
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.mcp import MCPServer, MCPServerStdio

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

async def run(mcp_server: MCPServer, query: str):

    # context = RunnerContext() 
    
    businessagent: Agent = Agent(
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
        model = "gpt-4o-mini",
    )
    
    business_result = await Runner.run(businessagent, query)
    # print("Business Result: ", business_result.final_output)    

    locationagent: Agent = Agent(
        name = 'Location Agent',
        instructions = """You are an assitant able to use the Google Maps tools that are available in the MCP server.. Use the tools and based on the business proposal, you need to find the top 3 locations for the business. 
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
        mcp_servers=[mcp_server],
        model = "gpt-4o-mini",
    )
    
    location_result = await Runner.run(locationagent, business_result.final_output)
    # print("Location Result: ", location_result.final_output)

    synthesizer_agent = Agent(
        name="synthesizer_agent",
        instructions="""You take the input and then output one JSON object (locations, competitors) without the ticks to pass it to our API for processing. 
                        Strictly use JSON format for competitors. Strictly use JSON format for the ideal locations.""",
        model = "gpt-4o-mini",
    )
    
    synthesizer_result = await Runner.run(synthesizer_agent, location_result.final_output)
    print("Synthesizer Result: \n", synthesizer_result.final_output)

    # result = await Runner.run(starting_agent=agent, input=query)
    # print(result.final_output)
    
async def main():
    # Ask the user for the directory path
    # query = input("Please enter the query: ")
    query = {
        "industry": "Food and Beverage",
        "product": "Coffee, Tea, Sides, Pastries",
        "location/city": "Manhattan, New York",
        "budget": "120000 - 300000",
        "size": "Small Enterprise",
        "unique_selling_proposition": "High Quality, Organic, Locally Sourced Ingredients"
    }
    query = "\n".join(f"{k}: {v}" for k, v in query.items())

    async with MCPServerStdio(
        cache_tools_list=True,  # Cache the tools list, for demonstration
        params={"command": "npx", "args": ["-y", "@modelcontextprotocol/server-google-maps"], "env": {"GOOGLE_MAPS_API_KEY": f"{GOOGLE_MAPS_API_KEY}"}},
    ) as server:
        # tools = await server.list_tools()
        # print(tools)
        with trace(workflow_name="MCP Google Maps - Location Intelligence for Business"):
            await run(server, query)


if __name__ == "__main__":
    asyncio.run(main())