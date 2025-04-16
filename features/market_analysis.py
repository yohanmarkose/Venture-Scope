import operator, json, os
from typing import TypedDict, Annotated, Optional, List, Union
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
from tavily import TavilyClient
from features.snowflake_analysis import SnowflakeConnector
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_core.messages import ToolCall, ToolMessage
from langchain_openai import ChatOpenAI
from functools import partial

from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(TAVILY_API_KEY)


required_env_vars = {
    'SNOWFLAKE_ACCOUNT': os.getenv('SNOWFLAKE_ACCOUNT'),
    'SNOWFLAKE_USER': os.getenv('SNOWFLAKE_USER'),
    'SNOWFLAKE_PASSWORD': os.getenv('SNOWFLAKE_PASSWORD'),
    'SNOWFLAKE_ROLE': os.getenv('SNOWFLAKE_ROLE'),
    'SNOWFLAKE_DB': os.getenv('SNOWFLAKE_DB'),
    'SNOWFLAKE_WAREHOUSE': os.getenv('SNOWFLAKE_WAREHOUSE'),
    'SNOWFLAKE_SCHEMA': os.getenv('SNOWFLAKE_SCHEMA')
}


## Creating the Agent State ##
class AgentState(TypedDict):
    chat_history: list[BaseMessage]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    industry: Optional[str]
    size_category: Optional[str]
    

@tool("vector_search")
def vector_search(query: str):
    """
    Searches for the most relevant chunks  in the Pinecone index based on the query.
    """
    pass
    # print("Reached Vector search 1")
    # top_k = 10
    # chunks = query_pinecone(query, top_k, year = year, quarter = quarter)
    # contexts = "\n---\n".join(
    #     {chr(10).join([f'Chunk {i+1}: {chunk}' for i, chunk in enumerate(chunks)])}
    # )
    # return contexts


@tool("web_search")
def web_search(query: str) -> str:
    """
    Searches the web for industry related information using Tavily API.
    The query should be used to understand the current trend in the industry.

    Args:
        query: The search query, related to the user inputted industry.
    
    Returns:
        JSON string containing search results.
    """
    try:
        response = tavily_client.search(query=query)
        return response
    
    except Exception as e:
        print(f"Error in web search: {str(e)}")
        return json.dumps({"results": []})


@tool("fetch_web_content")
def fetch_web_content(url: list) -> str:
    """
    Fetches content from the websites of top companies identified by snowflake_query tool.
    
    For each company retrieved by snowflake_query, use this tool to get detailed information
    from their websites. Extract key information for Competitor Details section.
    
    Args:
        url: List of URLs from the WEBSITE column of the snowflake_query output DataFrame
    
    Returns:
        Extracted content from the webpages for each company to populate Competitor Details section
    """
    try:
        response = tavily_client.extract(urls=url)
        return response["results"][0]["raw_content"]
    
    except Exception as e:
        print(f"Error in fetch web content: {str(e)}")
        return f"Error in fetch web content"


def format_result(result):
    
    parts = []
    
    if 'data' in result and result['data']:
        parts.append("DATA:")
        for i, item in enumerate(result['data'], start=1):
            parts.append(f"Record {i}:")
            for key, value in item.items():
                parts.append(f"  {key.title()}: {value}")
            parts.append("")  
    
    if 'summary' in result:
        parts.append("SUMMARY:")
        summary = result['summary'].strip()
        parts.append(summary)
        parts.append("")
    
    if 'analysis_type' in result:
        parts.append("Analysis Type:")
        analysis_type = result['analysis_type'].strip()
        parts.append(analysis_type)
    return "\n".join(parts)


@tool("snowflake_query")
def snowflake_query(industry: str = "financial services", size_category: str = None):
    """
    Fetches the top 5 companies in the specified industry from Snowflake database.
    
    This tool queries Snowflake for company data and returns a DataFrame containing:
    - COMPANY_NAME: Name of the company
    - SIZE: Size category of the company
    - WEBSITE: Company's website URL (important for fetch_web_content tool)
    - MARKET_CAP/PERFORMANCE_SCORE: Financial metrics based on size category
    
    Args:
        industry: The industry to analyze (e.g., "financial services")
        size_category: Company size filter ("small", "medium", "large")
    
    Returns:
        DataFrame containing top 5 companies with their details for displaying in Market Giants table
    """

    snow_obj = SnowflakeConnector(industry, size_category)
    snow_obj.connect()

    companies = snow_obj.get_company_data_by_industry(limit=10)
    print("df below\n", companies)

    if companies is not None:
        if size_category and size_category.lower() == "large":
            companies = companies[companies['MARKET_CAP'].notnull() & companies['T_SYMBOL'].notnull()]
            print(companies[['COMPANY_NAME', 'SIZE', 'WEBSITE', 'MARKET_CAP']].head(5))

            result = companies[['COMPANY_NAME', 'SIZE', 'WEBSITE', 'MARKET_CAP']]
        else:
            result = companies[['COMPANY_NAME', 'SIZE', 'WEBSITE', 'PERFORMANCE_SCORE']].head(5)
    
    return result


@tool("final_answer")
def final_answer(
    research_steps: str,
    market_giants: str,
    competitor_details: str,
    industry_overview: str,
    industry_trends: str,
    sources: str
):
    """
    Returns a comprehensive market analysis report for the specified industry.
    
    Args:
        research_steps: Bullet points explaining each research step taken with tool names
        market_giants: Markdown table of top 5 companies from snowflake_query (Company Name, Size, Market Cap/Performance)
        competitor_details: Detailed breakdown for each company with key points extracted from website content
        industry_overview: Overview of the industry based on all collected data
        industry_trends: Current and emerging trends in the industry from web search
        sources: List of all referenced sources with links where possible
    
    Returns:
        Structured dictionary with complete market analysis report organized in appropriate sections
    """
    if type(research_steps) is list:
        research_steps = "\n".join([f"- {r}" for r in research_steps])
    if type(sources) is list:
        sources = "\n".join([f"- {s}" for s in sources])
    
    report = {
        "research_steps": research_steps if research_steps else "",
        "market_giants": market_giants,
        "competitor_details": competitor_details,
        "industry_overview": industry_overview,
        "industry_trends": industry_trends,
        "sources": sources
    }

    return report


def init_research_agent(industry, size_category):
    tool_str_to_func = {
            "web_search": web_search,
            "fetch_web_content": fetch_web_content,
            "snowflake_query": snowflake_query,
            "final_answer": final_answer
        }
    
    tools = [web_search, fetch_web_content, snowflake_query, final_answer]


    ## Designing Agent Features and Prompt ##
    system_prompt = f"""You are a Market Analysis agent specializing in detailed industry research.
    Given the industry input '{industry}', follow this EXACT workflow:

    1. FIRST, use the snowflake_query tool to fetch the top 5 companies in this industry.
    2. SECOND, use the fetch_web_content tool with the website URLs from step 1.
    3. THIRD, use the web_search tool for additional industry insights.
    4. FINALLY, use the final_answer tool to compile a complete report.

    CRITICAL: You MUST complete ALL steps in order before returning results.
    DO NOT return intermediate results from any single tool.
    You MUST use the final_answer tool as the last step with complete report sections.

    Rules:
    - Complete all steps in sequence
    - Always use fetch_web_content after snowflake_query
    - Always use web_search after fetch_web_content
    - Always end with final_answer
    - Never skip steps in the workflow
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("assistant", "scratchpad: {scratchpad}"),
    ])

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=os.environ["OPENAI_API_KEY"],
        temperature=0
    )

    def create_scratchpad(intermediate_steps: list[AgentAction]):
        research_steps = []
        for i, action in enumerate(intermediate_steps):
            if action.log != "TBD":
                # this was the ToolExecution
                research_steps.append(
                    f"Tool: {action.tool}, input: {action.tool_input}\n"
                    f"Output: {action.log}"
                )
        return "\n---\n".join(research_steps)

    oracle = (
        {
            "industry": lambda x: x["industry"],
            "size_category": lambda x: x["size_category"],
            "chat_history": lambda x: x["chat_history"],
            "scratchpad": lambda x: create_scratchpad(
                    intermediate_steps=x["intermediate_steps"]
            ),
        }
        | prompt
        | llm.bind_tools(tools, tool_choice="any")
    )
    return oracle



## Router and Parent Agent functions
def run_oracle(state: AgentState, oracle):
    print("run_oracle")
    print(f"intermediate_steps: {state['intermediate_steps']}")
    out = oracle.invoke(state)
    tool_name = out.tool_calls[0]["name"]
    tool_args = out.tool_calls[0]["args"]
    action_out = AgentAction(
        tool=tool_name,
        tool_input=tool_args,
        log="TBD"
    )
    return {
        **state,
        "intermediate_steps": [action_out]
    }


def router(state: AgentState):
    # return the tool name to use
    
    if isinstance(state["intermediate_steps"], list):
        return state["intermediate_steps"][-1].tool
    else:
        # if we output bad format go to final answer
        print("Router invalid format")
        return "final_answer"
    


def run_tool(state: AgentState):
    tool_str_to_func = {
            "web_search": web_search,
            "fetch_web_content": fetch_web_content,
            "snowflake_query": snowflake_query,
            "final_answer": final_answer
        }
    
    
    # use this as helper function so we repeat less code
    tool_name = state["intermediate_steps"][-1].tool
    tool_args = state["intermediate_steps"][-1].tool_input

    # if tool_name in ["vector_search"]:
    #     tool_args = {
    #         **tool_args,
    #         "year": state.get("year"),
    #         "quarter": state.get("quarter")
    #     }
    print(f"{tool_name}.invoke(input={tool_args})")
    # run tool
    out = tool_str_to_func[tool_name].invoke(input=tool_args)
    action_out = AgentAction(
        tool=tool_name,
        tool_input=tool_args,
        log=str(out)
    )
    return {
        **state,
        "intermediate_steps": [action_out]
    }


## Langraph - Designing the Graph
def create_graph(research_agent):

    tools = [web_search, fetch_web_content, snowflake_query, final_answer]

    graph = StateGraph(AgentState)
    # Pass state to all functions that require it
    graph.add_node("oracle", partial(run_oracle, oracle=research_agent))
    graph.add_node("snowflake_query", run_tool)
    graph.add_node("fetch_web_content", run_tool)
    graph.add_node("web_search", run_tool)
    graph.add_node("final_answer", run_tool)

    # Set the entry point to start with the oracle
    graph.set_entry_point("oracle")
    
    # Add conditional edges based on the router function
    graph.add_conditional_edges(
        source="oracle",
        path=router,
    )
    
    # create edges from each tool back to the oracle
    for tool_obj in tools:
        if tool_obj.name != "final_answer":
            graph.add_edge(tool_obj.name, "oracle")

    # if anything goes to final answer, it must then move to END
    graph.add_edge("final_answer", END)

    # Compile the graph with increased recursion limit
    runnable = graph.compile()
    return runnable

def run_agents(industry=None, size_category=None):
    research_agent = init_research_agent(industry, size_category)
    runnable = create_graph(research_agent)
    return runnable