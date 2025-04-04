from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from langchain_openai import ChatOpenAI
import asyncio

from dotenv import load_dotenv
import os
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model="gpt-4o-mini")
model = ChatOpenAI(model="gpt-4o-mini")

async def main():
    async with MultiServerMCPClient(
        {
            "math": {
                "command": "python",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["math_server.py"],
                "transport": "stdio",
            }
            # "weather": {
            #     # make sure you start your weather server on port 8000
            #     "url": "http://localhost:8000/sse",
            #     "transport": "sse",
            # }
        }
    ) as client:
        agent = create_react_agent(model, client.get_tools())
        response = await agent.ainvoke({"messages": "what is 5 plus 46?"})
        for m in response["messages"]:
            m.pretty_print()

if __name__ == "__main__":
    asyncio.run(main())