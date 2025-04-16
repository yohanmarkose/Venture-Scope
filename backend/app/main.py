import io, os, time, base64, asyncio, json
from io import BytesIO
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple, Union
from features.mcp.google_maps.location_intelligence import start_location_intelligence
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
API_URL = "http://localhost:8000/"

# Models
class BusinessQuery(BaseModel):
    industry: str = Field(..., description="The industry sector of the business")
    product: List[str] = Field(..., description="Products or services offered by the business")
    location_city: List[str] = Field(..., alias="location/city", description="Geographic locations or cities of operation")
    budget: Tuple[int, int] = Field(..., description="Budget range in currency format (min, max)")
    size: str = Field(..., description="Size classification of the business")
    unique_selling_proposition: Optional[str] = Field(None, description="Key differentiators or unique value propositions")
    
    model_config = {
        "validate_by_name": True,
        "json_schema_extra": {
            "example": {
                "industry": "Food and Beverage",
                "product": ["Coffee", "Tea", "Pastries"],
                "location/city": ["Manhattan, New York"],
                "budget": [120000, 300000],
                "size": "Small Enterprise",
                "unique_selling_proposition": "High Quality, Organic, Locally Sourced Ingredients"
            }
        }
    }

class Competitor(BaseModel):
    name: str
    industry: str
    address: str
    size: str
    revenue: str
    market_share: str
    unique_selling_proposition: str
    growth_score: int
    customer_satisfaction_score: int
    reviews: List[str]
    rating: float

class Location(BaseModel):
    area: str
    city: str
    state: str
    population_density: str
    cost_of_living: str
    business_climate: str
    quality_of_life: str
    infrastructure: str
    suitability_score: int
    risk_score: int
    advantages: List[str]
    challenges: List[str]

class LocationIntelligenceResponse(BaseModel):
    locations: List[Location]
    competitors: List[Competitor]
    
async def async_send_to_api(session, api, data):
    """Send data to the API asynchronously and return the response"""
    try:
        async with session.post(f"{API_URL}/{api}", json=data, timeout=180) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        return {"error": str(e)}
    
def run_async_calls(api_calls):
    """Run multiple API calls asynchronously"""
    results = {}
    
    async def fetch_all():
        async with aiohttp.ClientSession() as session:
            tasks = []
            for api_name, api_endpoint, api_data in api_calls:
                task = asyncio.create_task(async_send_to_api(session, api_endpoint, api_data))
                tasks.append((api_name, task))
            
            # Wait for all tasks to complete
            for api_name, task in tasks:
                try:
                    results[api_name] = await task
                except Exception as e:
                    results[api_name] = {"error": str(e)}
    
    # Run the async event loop in a separate thread
    with ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, fetch_all())
        future.result()  # Wait for completion
        
    return results

# API Endpoints    

# Root endpoint to check if the server is running 
@app.get("/")
def read_root():
    return "Welcome to the Venture-Scope API!"

# Health check endpoint to verify the server status
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Endpoint to analyze location intelligence based on business query
@app.post("/location_intelligence", response_model=LocationIntelligenceResponse)
async def location_intelligence(query: BusinessQuery):
    try:
        # Format the query for agent processing
        formatted_query = {
            "industry": query.industry,
            "product": ", ".join(query.product),
            "location/city": ", ".join(query.location_city),
            "budget": f"{query.budget[0]} - {query.budget[1]}",
            "size": query.size,
            "unique_selling_proposition": query.unique_selling_proposition or ""
        }
        
        # Run the location intelligence pipeline
        result = await start_location_intelligence(formatted_query)
        
        # Validate the response has the expected structure
        if not isinstance(result, dict) or "locations" not in result or "competitors" not in result:
            raise ValueError("Invalid response structure from location intelligence pipeline")
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing location intelligence: {str(e)}")

from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
import os
from langchain.agents import Tool, initialize_agent
from langchain_community.chat_models import ChatOpenAI
from services.vectordb_expertchat import query_pinecone
from tavily import TavilyClient

router = APIRouter()

# ------------------ Models ------------------ #
class ExpertChatRequest(BaseModel):
    expert_key: str
    namespace: str
    question: str
    base_info: str
    model: str = "gpt-4o-mini"

# ------------------ Init Clients ------------------ #
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# ------------------ Tool Functions ------------------ #
def make_pinecone_tool(namespace):
    def tool_func(query: str):
        matches = query_pinecone(query, namespace=namespace, top_k=5)
        return "\n\n".join([m["metadata"]["text"] for m in matches if "text" in m.get("metadata", {})])
    return tool_func

def make_web_search_tool_for_expert(expert_key: str):
    if expert_key == "benhorowitz":
        return lambda query: strict_domain_web_search(query, domain="a16z.com")
    else:
        return None  

def strict_domain_web_search(query: str, domain: str):
    result = tavily.search(query=query)
    
    def is_preferred(res):
        return domain in res.get("url", "")

    if isinstance(result, dict) and "results" in result:
        filtered = list(filter(is_preferred, result["results"]))
        if filtered:
            return filtered[0]["content"]
        else:
            return f"No relevant results found from {domain}."
    return "⚠️ Unexpected web search result format."

# ------------------ Endpoint ------------------ #
@router.post("/chat_with_expert")
def chat_with_expert(request: ExpertChatRequest):
    try:
        expert_name = request.expert_key.replace("_", " ").title()
        base_info = request.base_info or f"You are {expert_name}, an industry expert."

        tools = [
            Tool(name="book_knowledge", func=make_pinecone_tool(request.namespace),
                 description="Use for questions based on the expert's published work."),
            Tool(name="web_search", func=make_web_search_tool_for_expert(request.expert_key),
                 description="Use for questions requiring real-time information or latest blogs from 2025")
        ]

        agent = initialize_agent(tools=tools, llm=llm, agent="chat-conversational-react-description", verbose=True ,handle_parsing_errors=True)

        final_prompt = f"""
        You are {expert_name}. {base_info}
        You have access to two sources of information:
        - book_knowledge: your published writings, talks, and expert-authored material
        - web_search: Your real time or latest blogs and articles

        Guidelines:
        - Use either book_knowledge or web_search not more than once — choose based on the complexity of the question.
        - All the responses generated should be in the first person
        - If the question is simple or based on personal experience, answer it directly.
        - Speak in a candid, wise, and occasionally humorous tone. Use examples, stories, and leadership lessons.
        - If the question is off-topic or irrelevant, respond with: "Sorry, I can’t help with that."

        Question: {request.question}
        """

        response = agent.invoke({
            "input": final_prompt,
            "chat_history": []  # optionally populate from request.chat_history
        })

        return {
            "answer": response["output"],
            "trace": response.get("intermediate_steps", [])
        }


    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

# ------------------ Register Router ------------------ #
app.include_router(router)
