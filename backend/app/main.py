import io, os, time, base64, asyncio
from io import BytesIO
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import pandas as pd

from features.ma_agent import run_agents

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

