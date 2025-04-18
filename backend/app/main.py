import io, os, time, base64, asyncio, json
from io import BytesIO
from fastapi import FastAPI, HTTPException , APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple, Union
from features.mcp.google_maps.location_intelligence import start_location_intelligence
from features.market_analysis import run_agents
from features.snowflake_analysis import SnowflakeConnector
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import openai
from dotenv import load_dotenv
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from langchain_core.messages import HumanMessage, AIMessage
import uuid
from features.qa_agent import create_qa_chatbot, handle_user_message_with_history
import warnings
from features.summary_agent import run_summary_agent
from services.s3 import S3FileManager

from langchain.agents import Tool, initialize_agent
from langchain_community.chat_models import ChatOpenAI
from services.vectordb_expertchat import query_pinecone
from tavily import TavilyClient

load_dotenv()

app = FastAPI()

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")


INDUSTRIES = [
    "accounting",
    "airlines/aviation",
    "alternative dispute resolution",
    "alternative medicine",
    "animation",
    "apparel & fashion",
    "architecture & planning",
    "arts and crafts",
    "automotive",
    "aviation & aerospace",
    "banking",
    "biotechnology",
    "broadcast media",
    "building materials",
    "business supplies and equipment",
    "capital markets",
    "chemicals",
    "civic & social organization",
    "civil engineering",
    "commercial real estate",
    "computer & network security",
    "computer games",
    "computer hardware",
    "computer networking",
    "computer software",
    "construction",
    "consumer electronics",
    "consumer goods",
    "consumer services",
    "cosmetics",
    "dairy",
    "defense & space",
    "design",
    "e-learning",
    "education management",
    "electrical/electronic manufacturing",
    "entertainment",
    "environmental services",
    "events services",
    "executive office",
    "facilities services",
    "farming",
    "financial services",
    "fine art",
    "fishery",
    "food & beverages",
    "food production",
    "fund-raising",
    "furniture",
    "gambling & casinos"
]

state_abbrev = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
}

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

class MessageItem(BaseModel):
    type: str  # "human" or "ai"
    content: str

class QuestionRequest(BaseModel):
    question: str
    industry: str
    product: List[str]
    location_city: List[str] = Field(..., alias="location/city")
    budget: List[float]
    size: str
    unique_selling_proposition: Optional[str] = None
    session_id: Optional[str] = None
    message_history: Optional[List[MessageItem]] = None
    
    model_config = {
        "populate_by_name": True
    }

class SummaryRecommendation(BaseModel):
    industry: str
    product: List[str]
    location_city: List[str]
    budget: List[float]
    size: str
    unique_selling_proposition: Optional[str] = None
    session_id: Optional[str] = None

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

# API Endpoints    

# Root endpoint to check if the server is running 
@app.get("/")
def read_root():
    return "Welcome to the Venture-Scope API!"

# Health check endpoint to verify the server status
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Endpoint to classify industry based on user input
def classify_industry(domain: str, products: list) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
A company operates in the domain of: {domain}.
They offer products or services such as: {', '.join(products)}.

From the following list of industries, pick the **one best matching industry**:
{', '.join(INDUSTRIES)}

Return ONLY one industry name from the list.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You classify companies into standard industries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        industry = response.choices[0].message.content.strip().lower()
        if industry in INDUSTRIES:
            return industry
        else:
            raise ValueError(f"Model returned an unrecognized industry: {industry}")
    except Exception as e:
        print(f"Error classifying industry: {e}")
        return None

# Function to convert report dictionary to markdown format
def convert_report_to_markdown(report_dict):
    """
    Converts a market analysis report dictionary to markdown format.
    
    Args:
        report_dict: Dictionary containing report sections
        
    Returns:
        String with markdown-formatted report
    """
    # Handle case where input might already be a string
    if isinstance(report_dict, str):
        try:
            # Try to parse it as JSON
            import json
            report_dict = json.loads(report_dict)
        except:
            # If not valid JSON, return as is
            return report_dict
    
    # Extract sections from dictionary with fallbacks for missing sections
    market_players = report_dict.get("market_players", "Market Players data not available")
    competitor_details = report_dict.get("competitor_details", "Competitor details not available")
    industry_overview = report_dict.get("industry_overview", "Industry overview not available")
    industry_trends = report_dict.get("industry_trends", "Industry trends not available")
    sources = report_dict.get("sources", "Sources not provided")
    
    # Format the markdown report
    markdown_report = f"""
# Market Analysis Report

## Market Players
{market_players}

## Competitor Details
{competitor_details}

## Industry Overview
{industry_overview}

## Industry Trends
{industry_trends}

## Sources
{sources}
""" 
    return markdown_report

def convert_summary_report_to_markdown(report_dict):
    try:
        # Parse the report if it's a string
        if isinstance(report_dict, str):
            report_dict = json.loads(report_dict)
        
        markdown = []
        
        # Add Executive Summary
        markdown.append("# Executive Summary")
        markdown.append(report_dict.get("executive_summary", ""))
        markdown.append("")
        
        # Add Market Analysis Insights
        markdown.append("## Market Analysis Insights")
        markdown.append(report_dict.get("market_analysis_insights", ""))
        markdown.append("")
        
        # Add Location Recommendations
        markdown.append("## Location Recommendations")
        markdown.append(report_dict.get("location_recommendations", ""))
        markdown.append("")
        
        # Add Action Steps
        markdown.append("## Action Steps")
        markdown.append(report_dict.get("action_steps", ""))
        markdown.append("")
        
        # Add Risk Assessment
        markdown.append("## Risk Assessment")
        markdown.append(report_dict.get("risk_assessment", ""))
        markdown.append("")
        
        # Add Resource Recommendations
        markdown.append("## Resource Recommendations")
        markdown.append(report_dict.get("resource_recommendations", ""))
        
        return "\n".join(markdown)
    except Exception as e:
        print(f"Error converting report to markdown: {str(e)}")
        return f"Error formatting report: {str(e)}"
    


def get_graph(industry):
    # ─── Fetch & prep ────────────────────────────────────────────────────────
    sf = SnowflakeConnector(industry)
    sf.connect()
    df = sf.get_statewise_count_by_industry(industry)
    sf.disconnect()

    # Title‐case and map to USPS code
    df['REGION'] = df['REGION'].str.title()
    unknown = set(df['REGION']) - set(state_abbrev)
    if unknown:
        warnings.warn(f"Unrecognized states: {unknown}")
    df['STATE_CODE'] = df['REGION'].map(state_abbrev)

    # Sum counts per state
    totals = (
        df
        .groupby(['REGION','STATE_CODE'], as_index=False)['COUNT']
        .sum()
    )

    # ─── Build choropleth ─────────────────────────────────────────────────────
    fig = go.Figure(go.Choropleth(
        locations=totals['STATE_CODE'],
        z=totals['COUNT'],
        locationmode='USA-states',
        colorscale='Viridis',
        colorbar_title='Total Companies',
        text=totals['REGION'],             # full state name
        hovertemplate=(
            '<b>%{text}</b><br>'
            'Total Companies: %{z}<extra></extra>'
        ),
        marker_line_color='white',
        marker_line_width=0.5,
    ))

    fig.update_layout(
        title=f"US {industry.title()} Companies by State",
        title_x=0.5,
        geo_scope='usa',
        height=600, width=950,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig

# Endpoint to analyze market based on business query
@app.post("/market_analysis")
def market_analysis(query: BusinessQuery):
    try:
        formatted_query = {
            "industry": query.industry,
            "product": ", ".join(query.product),
            "location/city": ", ".join(query.location_city),
            "budget": f"{query.budget[0]} - {query.budget[1]}",
            "size": query.size,
            "unique_selling_proposition": query.unique_selling_proposition or ""
        }
        size_category = formatted_query["size"]
        print("Size category selected is:", size_category)
        
        industry = classify_industry(formatted_query["industry"], formatted_query["product"])
        print("Industry selected is:", industry)

        fig_obj = get_graph(industry)

        runnable = run_agents(industry, size_category)
        out = runnable.invoke({ 
            "chat_history": [],
            "industry": industry,
            "size_category": size_category
        }, config={"recursion_limit": 70})

        answer = out["intermediate_steps"][-1].tool_input
        markdown_report = convert_report_to_markdown(answer)

        base_path = base_path = f"users/temp/"
        s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
        file = f"{base_path}market_analysis.md"
        s3_obj.upload_file(AWS_BUCKET_NAME, file, markdown_report)

        file_path = f"https://{s3_obj.bucket_name}.s3.amazonaws.com/{file}"
        # content = s3_obj.load_s3_file_content(file)

        print("Answer:\n", markdown_report)
        
        return {
            "answer": markdown_report,
            "plot": fig_obj.to_json(),
            "industry": industry,
            "file_path": file_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")


# Endpoint to analyze location intelligence based on business query
@app.post("/location_intelligence", response_model=LocationIntelligenceResponse)
async def location_intelligence(query: BusinessQuery):
    try:
        # Format the query for agent processing

        # Get industry from the domain and products
        industry = classify_industry(query.industry, query.product)
        
        formatted_query = {
            "industry": industry,
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


active_chatbots = {}
@app.post("/q_and_a")
def question_and_analysis(query: QuestionRequest):
    try:
        print(f"Received question: {query.question}")
        print(f"Session ID: {query.session_id}")
        
        # Process message history if provided
        message_history = []
        if query.message_history:
            print(f"Message history provided with {len(query.message_history)} items")
            for msg in query.message_history:
                if msg.type == "human":
                    message_history.append(HumanMessage(content=msg.content))
                elif msg.type == "ai":
                    message_history.append(AIMessage(content=msg.content))
        
        # If no history or only has AI messages, add the current question
        if not message_history or all(isinstance(msg, AIMessage) for msg in message_history):
            message_history.append(HumanMessage(content=query.question))
            
        # Prepare report data
        report_data = {
            "market_analysis": f"{query.industry}, {query.size}",
            "emerging_trends": query.industry,
            "location_intelligence": query.location_city,
            "recommendations": f"{query.industry}, {query.size}, {query.budget}"
        }
        print("Report data:", report_data)
        
        # Create or get existing chatbot session
        session_id = query.session_id or str(uuid.uuid4())
        print("Session ID:", session_id)
        
        if session_id not in active_chatbots:
            # Create new chatbot instance with the specific session ID
            print("Creating new chatbot instance")
            chatbot = create_qa_chatbot(report_data)
            print("Chatbot instance created")
            chatbot = chatbot.with_config(
                {"thread": {"configurable": {"session_id": session_id}}}
            )
            print("Chatbot instance configured")
            active_chatbots[session_id] = (chatbot, report_data)
            print("Chatbot instance stored")
        else:
            # Get existing chatbot
            chatbot, stored_report_data = active_chatbots[session_id]
            # Update report data if needed
            report_data = {**stored_report_data, **report_data}
            active_chatbots[session_id] = (chatbot, report_data)
        
        # Process the user's question with message history
        response = handle_user_message_with_history(chatbot, message_history, report_data)
        print("Response from chatbot:", response)
        
        return {
            "answer": response,
            "session_id": session_id
        }
    except Exception as e:
        import traceback
        print(f"Error in question_and_analysis: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")
    

@app.post("/summary_recommendations")
def final_analysis(query: SummaryRecommendation):
    try:
        formatted_query = {
            "industry": query.industry,
            "product": ", ".join(query.product),
            "location_city": ", ".join(query.location_city),
            "budget": f"{query.budget[0]} - {query.budget[1]}",
            "size": query.size,
            "unique_selling_proposition": query.unique_selling_proposition or ""
        }

        base_path = base_path = f"users/temp/"
        s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)
        file = f"{base_path}market_analysis.md"

        market_analysis_output = s3_obj.load_s3_file_content(file)

        location_intelligence_output = ", ".join(query.location_city)

        industry = classify_industry(formatted_query["industry"], formatted_query["product"])
        print("Industry selected is:", industry)

        runnable = run_summary_agent(industry, formatted_query["location_city"], formatted_query["budget"],
                     market_analysis_output, location_intelligence_output)
        out = runnable.invoke({ 
            "chat_history": [],
            "industry": industry,
            "location": formatted_query["location_city"],
            "budget_level": formatted_query["budget"],
            "market_analysis_output": market_analysis_output,
            "location_intelligence_output": location_intelligence_output,
            "intermediate_steps": []
        }, config={"recursion_limit": 70}) 
        
        # print("Raw output:", out)
        answer = out["intermediate_steps"][-1].tool_input
        markdown_report = convert_summary_report_to_markdown(answer)
        
        print("Final recommendations:\n", markdown_report)
        
        return {
            "answer": markdown_report,
            "industry": industry,
            "location": formatted_query["location_city"],
            "budget_level": formatted_query["budget"]
        }
    
    except Exception as e:
        print(f"Error in summary recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")
    

# router = APIRouter()

# # ------------------ Models ------------------ #
# class ExpertChatRequest(BaseModel):
#     expert_key: str
#     namespace: str
#     question: str
#     base_info: str
#     model: str = "gpt-4o-mini"

# # ------------------ Init Clients ------------------ #
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# # ------------------ Tool Functions ------------------ #
# def make_pinecone_tool(namespace):
#     def tool_func(query: str):
#         matches = query_pinecone(query, namespace=namespace, top_k=5)
#         return "\n\n".join([m["metadata"]["text"] for m in matches if "text" in m.get("metadata", {})])
#     return tool_func

# def make_web_search_tool_for_expert(expert_key: str):
#     if expert_key == "benhorowitz":
#         return lambda query: strict_domain_web_search(query, domain="a16z.com")
#     else:
#         return None  

# def strict_domain_web_search(query: str, domain: str):
#     result = tavily.search(query=query)
    
#     def is_preferred(res):
#         return domain in res.get("url", "")

#     if isinstance(result, dict) and "results" in result:
#         filtered = list(filter(is_preferred, result["results"]))
#         if filtered:
#             return filtered[0]["content"]
#         else:
#             return f"No relevant results found from {domain}."
#     return "⚠️ Unexpected web search result format."

# # ------------------ Endpoint ------------------ #
# @router.post("/chat_with_expert")
# def chat_with_expert(request: ExpertChatRequest):
#     try:
#         expert_name = request.expert_key.replace("_", " ").title()
#         base_info = request.base_info or f"You are {expert_name}, an industry expert."

#         tools = [
#             Tool(name="book_knowledge", func=make_pinecone_tool(request.namespace),
#                  description="Use for questions based on the expert's published work."),
#             Tool(name="web_search", func=make_web_search_tool_for_expert(request.expert_key),
#                  description="Use for questions requiring real-time information or latest blogs from 2025")
#         ]

#         agent = initialize_agent(tools=tools, llm=llm, agent="chat-conversational-react-description", verbose=True ,handle_parsing_errors=True)

#         final_prompt = f"""
#         You are {expert_name}. {base_info}
#         You have access to two sources of information:
#         - book_knowledge: your published writings, talks, and expert-authored material
#         - web_search: Your real time or latest blogs and articles

#         Guidelines:
#         - Use either book_knowledge or web_search not more than once — choose based on the complexity of the question.
#         - All the responses generated should be in the first person
#         - If the question is simple or based on personal experience, answer it directly.
#         - Speak in a candid, wise, and occasionally humorous tone. Use examples, stories, and leadership lessons.
#         - If the question is off-topic or irrelevant, respond with: "Sorry, I can’t help with that."

#         Question: {request.question}
#         """

#         response = agent.invoke({
#             "input": final_prompt,
#             "chat_history": []  # optionally populate from request.chat_history
#         })

#         return {
#             "answer": response["output"],
#             "trace": response.get("intermediate_steps", [])
#         }


#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

# # ------------------ Register Router ------------------ #
# app.include_router(router)
