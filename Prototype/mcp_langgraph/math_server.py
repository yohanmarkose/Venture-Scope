from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()


mcp_math = FastMCP("Math")

@mcp_math.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp_math.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

if __name__ == "__main__":
    mcp_math.run(transport="stdio")