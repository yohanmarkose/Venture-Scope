from typing import TypedDict, Annotated, Optional, List, Union
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
import operator
import json

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_core.messages import ToolCall, ToolMessage
from langchain_openai import ChatOpenAI
from functools import partial

from tavily import TavilyClient

from features.snowflake_analysis import SnowflakeConnector
# from features.pinecone_index import query_pinecone

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(TAVILY_API_KEY)

# State for Summary Agent
class SummaryAgentState(TypedDict):
    chat_history: list[BaseMessage]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    industry: Optional[str]
    location: Optional[str]
    budget_level: Optional[str]
    market_analysis_output: Optional[str]
    location_intelligence_output: Optional[str]
    emerging_trends_output: Optional[str]

# Tools for Summary Agent
@tool("vector_search")
def vector_search(query: str):
    """
    Searches for the most relevant chunks in the Pinecone index based on the query.
    This tool is used to retrieve VC advice and best practices.
    """
    pass
    # top_k = 5
    # chunks = query_pinecone(query, top_k)
    # contexts = "\n---\n".join(
    #     {chr(10).join([f'Chunk {i+1}: {chunk}' for i, chunk in enumerate(chunks)])}
    # )
    # return contexts

@tool("web_search")
def web_search(query: str) -> str:
    """
    Searches the web for specific information to support recommendations.
    Use this to find successful business strategies, case studies, or startup advice.

    Args:
        query: The search query related to business recommendations.
    
    Returns:
        JSON string containing search results.
    """
    try:
        response = tavily_client.search(query=query)
        return response
    
    except Exception as e:
        print(f"Error in web search: {str(e)}")
        return json.dumps({"results": []})

@tool("snowflake_real_estate")
def snowflake_real_estate(location: str = None, budget_level: str = None):
    """
    Fetches real estate data specific to the user's location preferences and budget.
    This tool provides detailed costs, availability, and property information.
    
    Args:
        location: The user's preferred business location
        budget_level: The user's budget level (low, mid, high)
    
    Returns:
        DataFrame with relevant real estate information
    """
    pass
    # snow_obj = SnowflakeConnector(location=location, budget_level=budget_level)
    # snow_obj.connect()
    
    # real_estate_data = snow_obj.get_real_estate_data()
    
    # if real_estate_data is not None:
    #     if budget_level and budget_level.lower() == "low":
    #         result = real_estate_data[['PROPERTY_TYPE', 'LOCATION', 'COST_PER_SQFT', 'AVAILABILITY']]
    #     elif budget_level and budget_level.lower() == "mid":
    #         result = real_estate_data[['PROPERTY_TYPE', 'LOCATION', 'COST_PER_SQFT', 'SIZE', 'AMENITIES']]
    #     else:  # high budget
    #         result = real_estate_data[['PROPERTY_TYPE', 'LOCATION', 'COST_PER_SQFT', 'SIZE', 'AMENITIES', 'PREMIUM_FEATURES']]
    
    # return result

@tool("final_recommendations")
def final_recommendations(
    executive_summary: str,
    market_analysis_insights: str,
    location_recommendations: str,
    action_steps: str,
    risk_assessment: str,
    resource_recommendations: str
):
    """
    Produces a comprehensive business recommendation report synthesizing all insights.
    
    Args:
        executive_summary: A concise overview of key findings (2-3 paragraphs)
        market_analysis_insights: Key insights from market analysis (bullet points)
        location_recommendations: Specific location recommendations with reasoning
        action_steps: Step-by-step plan for business establishment (numbered list)
        risk_assessment: Potential risks and mitigation strategies (table format)
        resource_recommendations: Suggested resources, tools, or partners
    
    Returns:
        Structured dictionary with final recommendation components
    """
    report = {
        "executive_summary": executive_summary,
        "market_analysis_insights": market_analysis_insights,
        "location_recommendations": location_recommendations,
        "action_steps": action_steps,
        "risk_assessment": risk_assessment,
        "resource_recommendations": resource_recommendations
    }
    
    return report

def init_summary_agent(industry, location, budget_level, market_analysis_output, location_intelligence_output):
    tools = [web_search, final_recommendations]
    
    ## Designing Agent Prompt
    system_prompt = f"""You are a Summary and Recommendations Agent that analyzes outputs from various business intelligence tools and synthesizes them into actionable business recommendations.

    You have access to outputs from two previous analyses:
    1. Market Analysis Output: Provides competitor analysis and market positioning
    2. Location Intelligence Output: Evaluates locations based on policy and real estate data

    Current Context:
    - Industry: {industry or 'Not specified'}
    - Location: {location or 'Not specified'}
    - Budget Level: {budget_level or 'Not specified'}

    Your task is to synthesize these outputs and provide a comprehensive business recommendation report. The report should include:

    1. An executive summary that captures the key insights
    2. A synthesis of market analysis insights
    3. Location recommendations with reasoning
    4. Step-by-step action plan for business establishment
    5. Risk assessment with mitigation strategies
    6. Recommended resources, tools, or partnerships

    Rules:
    - Base your recommendations on concrete data from the previous analyses
    - Prioritize findings based on the user's budget level and constraints
    - Provide recommendations that are specific, actionable, and realistic
    - Balance optimism with practical risk assessment
    - Do not repeat information verbatim; synthesize and transform it
    - Do not add bold or italics for any numerical values
    - If multiple locations were analyzed, recommend the best option with reasoning
    - Tailor your recommendations to the specific industry
    - For high-budget recommendations, focus on scalability and long-term growth
    - For low-budget recommendations, focus on efficiency and essential priorities

    Do NOT use any tool more than twice.

    Once you have collected sufficient information from various tools, use the final_recommendations tool to produce your comprehensive report.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "Market Analysis Output: {market_analysis_output}"),
        ("user", "Location Intelligence Output: {location_intelligence_output}"),
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
                research_steps.append(
                    f"Tool: {action.tool}, input: {action.tool_input}\n"
                    f"Output: {action.log}"
                )
        return "\n---\n".join(research_steps)

    oracle = (
        {
            "industry": lambda x: x["industry"],
            "location": lambda x: x["location"],
            "budget_level": lambda x: x["budget_level"],
            "market_analysis_output": lambda x: x["market_analysis_output"],
            "location_intelligence_output": lambda x: x["location_intelligence_output"],
            "chat_history": lambda x: x["chat_history"],
            "scratchpad": lambda x: create_scratchpad(
                    intermediate_steps=x["intermediate_steps"]
            ),
        }
        | prompt
        | llm.bind_tools(tools, tool_choice="any")
    )
    return oracle

# Router and execution functions (similar to MA agent)
def run_oracle(state: SummaryAgentState, oracle):
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

def router(state: SummaryAgentState):
    # return the tool name to use
    if isinstance(state["intermediate_steps"], list):
        return state["intermediate_steps"][-1].tool
    else:
        # if we output bad format go to final answer
        print("Router invalid format")
        return "final_recommendations"

def run_tool(state: SummaryAgentState):
    tool_str_to_func = {
        "web_search": web_search,
        "final_recommendations": final_recommendations
    }
    
    # helper function to reduce code repetition
    tool_name = state["intermediate_steps"][-1].tool
    tool_args = state["intermediate_steps"][-1].tool_input

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
def create_graph(summary_agent):
    # tools = [vector_search, web_search, snowflake_real_estate, final_recommendations]
    tools = [web_search, final_recommendations]

    graph = StateGraph(SummaryAgentState)

    # Pass state to all functions that require it
    graph.add_node("oracle", partial(run_oracle, oracle=summary_agent))
    # graph.add_node("vector_search", run_tool)
    graph.add_node("web_search", run_tool)
    # graph.add_node("snowflake_real_estate", run_tool)
    graph.add_node("final_recommendations", run_tool)

    graph.set_entry_point("oracle")

    graph.add_conditional_edges(
        source="oracle",
        path=router,
    )

    # create edges from each tool back to the oracle
    for tool_obj in tools:
        if tool_obj.name != "final_recommendations":
            graph.add_edge(tool_obj.name, "oracle")

    # if anything goes to final recommendations, it must then move to END
    graph.add_edge("final_recommendations", END)

    runnable = graph.compile()
    return runnable

def run_summary_agent(industry=None, location=None, budget_level=None, 
                     market_analysis_output=None, location_intelligence_output=None):
    """
    Main function to run the summary agent with all necessary inputs.
    
    Args:
        industry: The business domain or industry
        location: User's preferred location(s)
        budget_level: User's budget level (low, mid, high)
        market_analysis_output: Output from Market Analysis tab
        location_intelligence_output: Output from Location Intelligence tab
        
    Returns:
        The compiled runnable graph that can be executed
    """
    summary_agent = init_summary_agent(
        industry, 
        location, 
        budget_level, 
        market_analysis_output, 
        location_intelligence_output
    )
    runnable = create_graph(summary_agent)
    return runnable