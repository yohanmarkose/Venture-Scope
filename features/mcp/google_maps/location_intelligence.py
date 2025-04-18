import asyncio, json
import shutil, os
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.mcp import MCPServer, MCPServerStdio
from typing import Dict, Any

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

async def run_location_intelligence(mcp_server: MCPServer, query: str):
    """
    Run the location intelligence pipeline with the given query and MCP server.
    
    Args:
        mcp_server: The MCP server instance
        query: The query string in the format "key: value\nkey: value..."
        
    Returns:
        The processed location intelligence results as a dictionary
    """
    
    # Initialize the business agent with the provided query
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
    
    # Run the business agent with the provided query
    business_result = await Runner.run(businessagent, query)
    # print("Business Result: ", business_result.final_output)    
    
    # Initialize the location agent with the business result
    locationagent: Agent = Agent(
        name = 'Location Agent',
        instructions = """You are an assitant able to use the Google Maps tools that are available in the MCP server. Use the tools and based on the business proposal, you need to find the top 3 locations for the business. 
                            Identify competitors in these said locations to support your decisions.
                            The output strictly has to be JSON formatted. 
                            You need to provide a list of places that are suitable for the business in and around the mentioned cities. 
                                The list should strictly include the following: 
                                    1. Area
                                    2. City
                                    3. State
                                    4. Population Density (Low, Medium, High)
                                    5. Cost of Living (Low, Medium, High)
                                    6. Business Climate
                                    7. Quality of Life
                                    8. Infrastructure
                                    9. Suitability Score (1-10)
                                    10. Risk Score (1-10)
                                    11. Advantages [List] (in detail)
                                    12. Challenges [List] (in detail)
                                    13. Competitors 
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
                        Strictly use JSON format for the ideal locations. Strictly use JSON format for the competitors. Valid JSON format {locations: [], competitors: []}.
                        JSON formatted keys should be in snake_case.""",
        model = "gpt-4o-mini",
    )
    
    synthesizer_result = await Runner.run(synthesizer_agent, location_result.final_output)
    print("Synthesizer Result: \n", synthesizer_result.final_output)
    # print("Synthesizer Result Type: ", type(synthesizer_result.final_output))
    
    # Process the output to ensure it's a proper Python dictionary
    if isinstance(synthesizer_result.final_output, str):
        # Remove any markdown code block formatting if present
        json_str = synthesizer_result.final_output
        if "```json" in json_str:
            json_str = json_str.split("```json")[1]
        if "```" in json_str:
            json_str = json_str.split("```")[0]
        
        # Parse the JSON string
        try:
            result = json.loads(json_str.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON output from agents: {str(e)}")
    else:
        result = synthesizer_result.final_output
    return result
    

async def start_location_intelligence(query_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start the location intelligence analysis from a query dictionary.
    This function is meant to be called from FastAPI.
    
    Args:
        query_dict: Dictionary containing the query parameters
        
    Returns:
        Dictionary containing the location intelligence results
    """
    
    # Format the query for agent processing
    query_str = "\n".join(f"{k}: {v}" for k, v in query_dict.items())
    
    async with MCPServerStdio(
        cache_tools_list=True,
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-google-maps"], 
            "env": {"GOOGLE_MAPS_API_KEY": f"{GOOGLE_MAPS_API_KEY}"}
        },
    ) as server:
        with trace(workflow_name="MCP Google Maps - Location Intelligence for Business"):
            return await run_location_intelligence(server, query_str)


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
    # query = "\n".join(f"{k}: {v}" for k, v in query.items())
    
    # Run the location intelligence analysis
    result = await start_location_intelligence(query)
    return result


if __name__ == "__main__":
    print(asyncio.run(main()))