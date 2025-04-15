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

class MarketAnalysisRequest(BaseModel):
    domain: str
    products: list
    size_category: str

app = FastAPI()


PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_FILE_INDEX = os.getenv("PINECONE_FILE_INDEX")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

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


@app.post("/market_analysis")
def query_nvdia_documents(request: MarketAnalysisRequest):
    try:
        size_category = request.size_category
        
        # Get industry from the domain and products
        industry = classify_industry(request.domain, request.products)
        print("Industry selected is:", industry)    

        runnable = run_agents(industry, size_category)
        out = runnable.invoke({ 
            "chat_history": [],
            "industry": industry,
            "size_category": size_category
        })

        print(out)
        answer = out["intermediate_steps"][-1].tool_input

        markdown_report = convert_report_to_markdown(answer)

        print("Answer:\n", markdown_report)
        
        return {
            "answer": markdown_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")


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
    research_steps = report_dict.get("research_steps", "Research methodology not provided")
    market_giants = report_dict.get("market_giants", "Market giants data not available")
    competitor_details = report_dict.get("competitor_details", "Competitor details not available")
    industry_overview = report_dict.get("industry_overview", "Industry overview not available")
    industry_trends = report_dict.get("industry_trends", "Industry trends not available")
    sources = report_dict.get("sources", "Sources not provided")
    
    # Format the markdown report
    markdown_report = f"""
# Market Analysis Report

## Research Methodology
{research_steps}

## Market Giants
{market_giants}

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

if __name__ == "__main__":
    industry = classify_industry("Technology and services", ["smartphone", "laptop", "tablet"])
    print("Classified industry:", industry)

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
    
