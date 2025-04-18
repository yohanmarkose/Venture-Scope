
import asyncio, json
import shutil, os
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.mcp import MCPServer, MCPServerStdio
from typing import Dict, Any

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

GOOGLE_SEARCH_ENGINE_ID=os.getenv("GOOGLE_SEARCH_ENGINE_ID")
GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")

async def main(query):
    async with MCPServerStdio(
        cache_tools_list=True,
        params={
            "command": "npx",
            "args": ["-y", "@adenot/mcp-google-search"], 
            "env": {"GOOGLE_SEARCH_ENGINE_ID": f"{GOOGLE_SEARCH_ENGINE_ID}",
                    "GOOGLE_API_KEY": f"{GOOGLE_API_KEY}"}
        },
    ) as server:
        with trace(workflow_name="MCP Google Search"):
            print(await server.list_tools())
            searchagent: Agent = Agent(name="Google Search Agent",
                                       instructions="You are a Google Search Agent. You will receive a query and return the results in JSON format.",
                                       mcp_servers=[server],
                                       model="gpt-4o-mini")
            results = await Runner.run(searchagent, query)
            print("Results: ", results.final_output)
    
if __name__ == "__main__":
    print(asyncio.run(main(input("Enter your query: "))))