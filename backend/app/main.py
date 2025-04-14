import io, os, time, base64, asyncio, json
from io import BytesIO
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple, Union
from features.mcp.google_maps.location_intelligence import start_location_intelligence
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

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
@app.post("/analyze_location", response_model=LocationIntelligenceResponse)
async def analyze_location(query: BusinessQuery):
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
    
