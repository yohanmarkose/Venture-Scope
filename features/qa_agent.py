import operator, json, os
from typing import TypedDict, Annotated, Optional, List, Dict, Any, Union
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
from tavily import TavilyClient
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_core.messages import ToolCall, ToolMessage
from langchain_openai import ChatOpenAI
from functools import partial
from features.vector_db.pinecone_index import query_pinecone
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(TAVILY_API_KEY)

## Creating the Agent State ##
class ChatbotState(TypedDict):
    chat_history: list[BaseMessage]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    report_data: Dict[str, Any]  # To store previously generated report data
    tool_calls_count: int  # Track number of tool calls in a single turn

@tool("web_search")
def web_search(query: str) -> str:
    """
    Searches the web for information related to the user's question.
    
    Args:
        query: The search query related to the user's question.
    
    Returns:
        JSON string containing search results.
    """
    try:
        print("using web_search")
        response = tavily_client.search(query=query, limit=5)
        output_string = ""
        if 'results' in response:
            for i, result in enumerate(response['results']):
                # Extract the required fields
                title = result.get('title', '')
                url = result.get('url', '')
                content = result.get('content', '')
                
                # Format each result and add to the output string
                output_string += f'Title: {title} \n URL: {url} \n Content: {content}'
                
                # Add a separator between results (except after the last one)
                if i < len(response['results']) - 1:
                    output_string += '\n\n'
            return output_string
        return "No results found"
    
    except Exception as e:
        print(f"Error in web search: {str(e)}")
        return f"Error in web search: {str(e)}"

@tool("fetch_web_content")
def fetch_web_content(url: list) -> str:
    """
    Fetches the content from the provided URLs for more detailed information.
    
    Args:
        url: List of URLs to fetch content from.
    
    Returns:
        The extracted content from the webpages.
    """
    try:
        print("using fetch_web_content")
        response = tavily_client.extract(urls=url)
        return response["results"][0]["raw_content"]
    
    except Exception as e:
        print(f"Error in fetch web content: {str(e)}")
        return f"Error in fetch web content: {str(e)}"
    
@tool("vector_search")
def vector_search(query: str):
    """
    Searches for the most relevant information chunks in the Pinecone vector database containing venture capital reports.
    
    This tool performs semantic search on VC industry data, including market trends, investment statistics, 
    fundraising insights, and regulatory information. It returns the top most relevant text chunks 
    that match the user's query about venture capital, startup funding, or industry-specific information.
    
    Args:
        query (str): The user's search query about venture capital topics, industry trends, or related questions
        
    Returns:
        str: A formatted string containing the most relevant text chunks from the VC reports database
    """
    print("Reached Vector search 1")
    top_k = 10
    chunks = query_pinecone(query, top_k)
    contexts = "\n---\n".join(
        {chr(10).join([f'Chunk {i+1}: {chunk}' for i, chunk in enumerate(chunks)])}
    )
    print("vector contexts", contexts)
    return contexts

@tool("final_answer")
def final_answer(answer: str):
    """
    Provides a final answer to the user's question based on the report data and additional research.
    
    Args:
        answer: The concise answer to the user's question, including any relevant information
               from the report data and additional research.
    
    Returns:
        The final answer formatted for presentation to the user.
    """
    return answer

def init_chatbot_agent(report_data):
    """Initialize the chatbot agent with the report data"""
    
    tools = [web_search, fetch_web_content, vector_search, final_answer]

    system_prompt = """You are a Q&A assistant that helps users understand business market analysis reports.

    Context:
    - You have access to the following report data: {report_data}
    - Available tools:
    - web_search: Search web for user question-related information
    - fetch_web_content: Get detailed content from specific URLs
    - vector_search: Find VC advice, market trends and investment data
    - final_answer: Provide your final response

    PROCESS:
    1. First try answering directly from report data
    2. Use tools only if report data lacks information
    3. Provide final answer after gathering sufficient information

    RESPONSE STYLE:
    - Be concise and direct
    - Use 1-3 sentences for most answers
    - Only elaborate when asked or necessary
    - Use bullet points for lists, not paragraphs
    - Cite sources when using external information

    RULES:
    - Maximum 2 tool uses per conversation turn
    - Keep answers brief but accurate
    - Use final_answer tool for your response
    - If you don't know, say so briefly
    - Never make up information
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("assistant", "Working memory: {scratchpad}"),
    ])

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=os.environ["OPENAI_API_KEY"],
        temperature=0.2
    )

    def create_scratchpad(intermediate_steps: list[tuple[AgentAction, str]]):
        research_steps = []
        for i, (action, output) in enumerate(intermediate_steps):
            research_steps.append(
                f"Tool: {action.tool}, input: {action.tool_input}\n"
                f"Output: {output}"
            )
        return "\n---\n".join(research_steps)

    chatbot = (
        {
            "report_data": lambda x: x["report_data"],
            "chat_history": lambda x: x["chat_history"],
            "scratchpad": lambda x: create_scratchpad(
                    intermediate_steps=x["intermediate_steps"]
            ),
        }
        | prompt
        | llm.bind_tools(tools, tool_choice="auto")
    )
    return chatbot

## Router and Parent Agent functions
def run_oracle(state: ChatbotState, oracle):
    print("run_oracle")
    print(f"intermediate_steps: {state['intermediate_steps']}")
    out = oracle.invoke(state)
    
    # Check if we have tool calls
    if hasattr(out, 'tool_calls') and out.tool_calls:
        tool_name = out.tool_calls[0]["name"]
        tool_args = out.tool_calls[0]["args"]
        action = AgentAction(
            tool=tool_name,
            tool_input=tool_args,
            log="TBD"
        )
        # Track tool calls
        tool_calls_count = state.get("tool_calls_count", 0) + 1
        
        return {
            **state,
            "intermediate_steps": state["intermediate_steps"] + [(action, "")],
            "tool_calls_count": tool_calls_count
        }
    else:
        # If no tool calls, use final_answer
        action = AgentAction(
            tool="final_answer",
            tool_input=out.content,
            log="TBD"
        )
        return {
            **state,
            "intermediate_steps": state["intermediate_steps"] + [(action, "")]
        }

def router(state: ChatbotState):
    # Check tool call limit
    if state.get("tool_calls_count", 0) >= 5:
        return "final_answer"
    
    # Get the last tool used
    last_step = state["intermediate_steps"][-1]
    
    if isinstance(last_step, tuple):
        action, output = last_step
        return action.tool
    else:
        # If format is wrong, go to final_answer
        print("Router invalid format")
        return "final_answer"

def run_tool(state: ChatbotState):
    tool_str_to_func = {
        "web_search": web_search,
        "fetch_web_content": fetch_web_content,
        "vector_search": vector_search,
        "final_answer": final_answer
    }
    
    # Get the last action
    last_action, _ = state["intermediate_steps"][-1]
    
    tool_name = last_action.tool
    tool_args = last_action.tool_input
    
    print(f"{tool_name}.invoke(input={tool_args})")
    
    # Run tool
    out = tool_str_to_func[tool_name](tool_args)
    
    # Update the intermediate steps with the result
    updated_steps = state["intermediate_steps"][:-1]
    updated_steps.append((last_action, str(out)))
    
    return {
        **state,
        "intermediate_steps": updated_steps
    }

## Langraph - Designing the Graph
def create_graph(chatbot_agent):
    tools = [web_search, fetch_web_content, vector_search, final_answer]

    graph = StateGraph(ChatbotState)
    
    # Add nodes
    graph.add_node("oracle", partial(run_oracle, oracle=chatbot_agent))
    graph.add_node("web_search", run_tool)
    graph.add_node("fetch_web_content", run_tool)
    graph.add_node("vector_search", run_tool)
    graph.add_node("final_answer", run_tool)

    # Set the entry point to start with the oracle
    graph.set_entry_point("oracle")
    
    # Add conditional edges based on the router function
    graph.add_conditional_edges(
        source="oracle",
        path=router,
    )
    
    # Create edges from each tool back to the oracle
    for tool_obj in tools:
        if tool_obj.name != "final_answer":
            graph.add_edge(tool_obj.name, "oracle")

    # If anything goes to final_answer, it must then move to END
    graph.add_edge("final_answer", END)

    # Compile the graph
    runnable = graph.compile()
    return runnable

def run_chatbot(report_data=None):
    chatbot_agent = init_chatbot_agent(report_data)
    runnable = create_graph(chatbot_agent)
    return runnable