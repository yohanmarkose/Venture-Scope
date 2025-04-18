from pydantic import BaseModel
from fastapi import HTTPException
from langchain.agents import Tool, initialize_agent
from langchain_openai import ChatOpenAI

import os
from services.vectordb_expertchat import query_pinecone
from tavily import TavilyClient

class ExpertChatRequest(BaseModel):
    expert_key: str
    question: str
    base_info: str
    model: str = "gpt-4o-mini"

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def make_pinecone_tool(expert_key):
    def tool_func(query: str):
        matches = query_pinecone(query, namespace=expert_key, top_k=5)
        return "\n\n".join([m["metadata"]["text"] for m in matches if "text" in m.get("metadata", {})])
    return tool_func

def make_web_search_tool(expert_key):
    if expert_key == "BenHorowitz":
        domain="https://a16z.com/news-content/"
        return lambda query: strict_domain_web_search(query, domain)
    elif expert_key == "MarkCuban":
        domain="https://blogmaverick.com/"
        return lambda query: strict_domain_web_search(query, domain)
    elif expert_key == "ReedHastings":
        return None
    elif expert_key == "SamWalton":
        return None
    return None

def strict_domain_web_search(query, domain):
    from urllib.parse import urlparse

    target_domain = urlparse(domain).netloc  # e.g., 'a16z.com'
    print(f"Searching ONLY within domain: {target_domain}")

    # Direct domain-limited search
    result = tavily.search(query=query, include_domains=[target_domain])
    
    if isinstance(result, dict) and "results" in result:
        for res in result["results"]:
            res_url = res.get("url", "")
            print(f"🔍 Result URL: {res_url}")
            return res.get("content", "No content found.")
        
        return f"No relevant results found from {target_domain}."
    
    return "⚠️ Unexpected web search result format."

def chat_with_expert_endpoint(request: ExpertChatRequest):
    try:
        expert_name = request.expert_key.replace("_", " ").title()
        base_info = request.base_info or f"You are {expert_name}, an industry expert."

        tools = [
            Tool(
                name="book_knowledge",
                func=make_pinecone_tool(request.expert_key),
                description="Use for questions based on the expert's published work."
            )
        ]

        web_tool = make_web_search_tool(request.expert_key)
        if web_tool:
            tools.append(
                Tool(
                    name="web_search",
                    func=web_tool,
                    description="Use for questions requiring recent blogs or real-time information."
                )
            )

        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent="chat-conversational-react-description",
            verbose=True,
            handle_parsing_errors=True
        )

        expert_prompt = f"""
        You are {expert_name}. {base_info}
        You have access to two tools they ranked in order of preference:
        - 1. book_knowledge: your own material, interviews, and writings
        - 2. web_search: current events, blogs or online knowledge
        
        Rules:
        - Analyse the question and decide if {expert_name} has a significant connection.
        - If questions is off-topic, say: "Sorry, I can’t help with that."
        - Answers should be concise and conversational of {expert_name}'s style try to use the exact words used by {expert_name}.
        - Give examples from {expert_name}'s experience when possible.
        - Speak in first person, as if you are {expert_name}.
        
        Question: {request.question}
        """

        response = agent.invoke({
            "input": expert_prompt,
            "chat_history": []
        })

        return {
            "answer": response["output"],
            "expert": expert_name,
            "tools_used": [tool.name for tool in tools],
            "trace": response.get("intermediate_steps", [])
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")