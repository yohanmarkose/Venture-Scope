from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator
import json

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from functools import partial


from tavily import TavilyClient

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(TAVILY_API_KEY)

# Creating the Agent State with thread memory
class ChatbotState(TypedDict):
    messages: List[BaseMessage]
    intermediate_steps: Annotated[List[tuple[AgentAction, str]], operator.add]
    report_data: Dict[str, Any]  # To store previously generated report data

# Tool definitions
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
        response = tavily_client.search(query=query)
        return response
    
    except Exception as e:
        print(f"Error in web search: {str(e)}")
        return json.dumps({"results": []})

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
        response = tavily_client.extract(urls=url)
        return response["results"][0]["raw_content"]
    
    except Exception as e:
        print(f"Error in fetch web content: {str(e)}")
        return f"Error in fetch web content"

def init_chatbot_agent(report_data):
    """Initialize the chatbot agent with the report data"""
    
    tools = [web_search, fetch_web_content]

    system_prompt = """You are a helpful Q&A assistant that helps users understand their business market analysis reports and answer additional questions.
    
    You have access to previously generated market analysis reports and tools to search for additional information.
    
    Context:
    - You have the following report data: {report_data}
    
    Rules:
    - Use a conversational tone suitable for a chatbot interaction.
    - Provide concise but informative responses.
    - If searching for additional information, explain why you're doing so.
    - Maintain the conversation history to provide contextually relevant responses.
    - Cite sources when providing information from external websites.
    - Do not use any tool more than twice in a single conversation turn.
    - Always refer to previous interactions in the conversation if relevant.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("assistant", "Working memory: {scratchpad}"),
    ])

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.2
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

    chatbot = (
        {
            "report_data": lambda x: x["report_data"],
            "messages": lambda x: x["messages"],
            "scratchpad": lambda x: create_scratchpad(
                    intermediate_steps=x["intermediate_steps"]
            ),
        }
        | prompt
        | llm.bind_tools(tools, tool_choice="auto")
    )
    return chatbot

def agent_should_continue(state: ChatbotState) -> bool:
    """Determine if the agent should continue or respond to the user"""
    # Check if the last message contains a tool call
    if len(state["intermediate_steps"]) == 0:
        return False
    
    last_action = state["intermediate_steps"][-1]
    # Get the last assistant message content
    messages = state["messages"]
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            # If there's no tool call or the last action used "fetch_web_content"
            # which is typically the last tool used before responding
            if not hasattr(msg, 'tool_calls') or last_action.tool == "fetch_web_content":
                return False
            break
    
    return True

def run_agent(state: ChatbotState, chatbot):
    """Run the chatbot agent to process the user's message"""
    print("Running chatbot agent")
    out = chatbot.invoke(state, config={"recursion_limit": 70})
    
    # Check if the response contains tool calls
    if hasattr(out, 'tool_calls') and len(out.tool_calls) > 0:
        tool_call = out.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        action_out = AgentAction(
            tool=tool_name,
            tool_input=tool_args,
            log="TBD"
        )
        
        # Update intermediate steps with the new action
        return {
            **state,
            "intermediate_steps": state["intermediate_steps"] + [action_out]
        }
    else:
        # If no tool calls, add the response to messages and clear intermediate steps
        return {
            **state,
            "messages": state["messages"] + [out],
            "intermediate_steps": []
        }

def run_tool(state: ChatbotState):
    """Execute the tool specified in the last intermediate step"""
    tool_str_to_func = {
        "web_search": web_search,
        "fetch_web_content": fetch_web_content
    }
    
    # Get the last action from intermediate steps
    last_action = state["intermediate_steps"][-1]
    tool_name = last_action.tool
    tool_args = last_action.tool_input

    print(f"Executing {tool_name} with args: {tool_args}")
    
    # Run the tool
    out = tool_str_to_func[tool_name].invoke(input=tool_args)
    
    # Update the action with the tool output
    updated_action = AgentAction(
        tool=tool_name,
        tool_input=tool_args,
        log=str(out)
    )
    
    # Replace the last action in intermediate steps with the updated action
    return {
        **state,
        "intermediate_steps": state["intermediate_steps"][:-1] + [updated_action]
    }

def router(state: ChatbotState):
    """Router function to determine the next node in the graph"""
    try:
        if len(state["intermediate_steps"]) == 0:
            return END
        last_action = state["intermediate_steps"][-1]
        if last_action.log == "TBD":
            return last_action.tool
        else:
            return "agent"
    except Exception as e:
        print(f"Error in router: {str(e)}")
        return END

def create_chatbot_graph(chatbot_agent):
    """Create the LangGraph for the chatbot with memory"""
    try:
        print("Starting graph creation")
        # Define tools directly
        tool_names = ["web_search", "fetch_web_content"]
        
        # Create the state graph
        print("Creating StateGraph")
        graph = StateGraph(ChatbotState)
        print("StateGraph created")
        
        # Add nodes
        print("Adding agent node")
        graph.add_node("agent", partial(run_agent, chatbot=chatbot_agent))
        print("Agent node added")
        
        print("Adding web_search node")
        graph.add_node("web_search", run_tool)
        print("web_search node added")
        
        print("Adding fetch_web_content node")
        graph.add_node("fetch_web_content", run_tool)
        print("fetch_web_content node added")
        
        # Set the entry point
        print("Setting entry point")
        graph.set_entry_point("agent")
        print("Entry point set")
        
        # Add conditional edges from agent
        print("Adding conditional edges")
        graph.add_conditional_edges(
            source="agent",
            path=router
        )
        print("Conditional edges added")
        
        # Add edges from tools back to the agent
        print("Adding tool edges")
        for tool_name in tool_names:
            print(f"Adding edge from {tool_name} to agent")
            graph.add_edge(tool_name, "agent")
        print("Tool edges added")
        
        # Compile the graph
        print("Compiling graph")
        runnable = graph.compile()
        print("Graph compiled")
        
        return runnable
    except Exception as e:
        print(f"Error in create_chatbot_graph: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise


def create_qa_chatbot(report_data=None):
    """Main function to create and return the chatbot with the report data"""
    if report_data is None:
        report_data = {}
    print("Creating chatbot agent")
    chatbot_agent = init_chatbot_agent(report_data)
    print("Chatbot agent initialized")
    runnable_graph = create_chatbot_graph(chatbot_agent)
    print("Graph created")
    
    # Create a stateful runnable with memory using thread
    stateful_runnable = runnable_graph.with_config(
        {"thread": {"configurable": {"session_id": "chatbot_session"}}}
    )
    
    return stateful_runnable

def handle_user_message_with_history(chatbot, message_history, report_data=None):
    """
    Handle a user message with full conversation history and return the chatbot response.
    
    Args:
        chatbot: The configured chatbot instance
        message_history: List of message objects (HumanMessage, AIMessage)
        report_data: Dictionary of report data for context
        
    Returns:
        The chatbot's response text
    """
    if report_data is None:
        report_data = {}
    
    print(f"Handling user message with {len(message_history)} messages in history")
    
    # Create the initial state with the complete message history
    initial_state = {
        "messages": message_history,
        "intermediate_steps": [],
        "report_data": report_data
    }
    
    print("Initial state created with message history")
    
    # Process the message through the graph
    try:
        result = chatbot.invoke(initial_state)
        print("Graph invoked successfully")
        
        # Extract the chatbot's response messages (should be the last AI message)
        response_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        
        # Return the latest response
        if response_messages:
            return response_messages[-1].content
        else:
            return "I'm sorry, I couldn't process your request."
    except Exception as e:
        import traceback
        print(f"Error in handle_user_message_with_history: {str(e)}")
        print(traceback.format_exc())
        return f"I encountered an error while processing your request. Please try again."