# Venture Scope

Venture Scope is a comprehensive business intelligence platform designed to help entrepreneurs and businesses make data-driven decisions about market opportunities, location intelligence, and competitor analysis. The platform integrates advanced analytics, machine learning, and natural language processing to provide actionable insights.

## Project Overview

To create a comprehensive startup advisory system, the project integrates data from Free Company Dataset (Snowflake) combining with yfinance to fetch financial side of data for available companies. Along with MCP-integration of google maps to figure out the rich details on the ideal or potential locations for the user. These reports are supported by Q&A agents along with VC investment quarterly reports to address and serve as a platform that will provide users with a base for questing and analyzing his interest in specified business domains, company size parameters, and location preferences to generate tailored recommendations and insights.

## Deployed Links

- [Streamlit](https://venture-scope.streamlit.app/?embed_options=light_theme)

- [FastAPI](https://venture-scope-969760129380.us-central1.run.app)

- [Airflow](http://34.31.90.252:8080/home)

- [Codelabs](https://codelabs-preview.appspot.com/?file_id=1BaeKci7nt9ODAldre-vneEculW-P1jrT8MIS0doFl_s#11)

- [Project Document](https://docs.google.com/document/d/1BaeKci7nt9ODAldre-vneEculW-P1jrT8MIS0doFl_s/edit?tab=t.0)

- [Video Walkthrough](https://northeastern-my.sharepoint.com/:v:/g/personal/gangurde_a_northeastern_edu/EfdzaIhppLNGgY2jeJWwTyABnL_a06F4qwEhP3bRorFFGw?e=tk4avl&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJTdHJlYW1XZWJBcHAiLCJyZWZlcnJhbFZpZXciOiJTaGFyZURpYWxvZy1MaW5rIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXcifX0%3D)

## Architecture Diagram
![architecture_diagram](https://github.com/user-attachments/assets/28b256b1-4322-4d50-9c11-8f639febc9a8)



## Features

- **Market Analysis**: Gain insights into market trends, consumer behavior, and growth opportunities.
- **Location Intelligence**: Identify optimal business locations based on demographics, competition, and other factors.
- **Competitor Analysis**: Understand competitors' strengths and weaknesses to develop effective strategies.
- **Q&A Chatbot**: Ask questions about your business analysis and get personalized answers.
- **Expert Chat**: Interact with virtual representations of industry experts for advice and insights.
 
## Getting Started

### Prerequisites

- Python 3.10+
- Docker
- Node.js (for MCP server if required)
- AWS credentials for S3 integration
- OpenAI API key for embeddings and chat models

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/venture-scope.git
cd venture-scope
```
Set up the environment variables:

2. Install dependencies:
```
pip install -r requirements.txt
```
3. Set up the Airflow environment:
```
cd airflow
docker-compose up
```
4. Run the frontend:
```
cd frontend
streamlit run app.py
```
5. Start the backend:
```
cd backend
uvicorn app.main:app --reload
```

### Usage
Open the Streamlit frontend at http://localhost:8501.
Configure your business details in the sidebar.
Generate insights, analyze locations, and interact with the Q&A chatbot or expert chat.

### API Endpoints
The backend provides several endpoints for analysis:
```
/market_analysis: Analyze market trends and competitors.
/location_intelligence: Get location-specific insights.
/q_and_a: Ask questions and get answers based on generated reports.
/chat_with_experts: Generate a comprehensive business summary.
```

### Technologies Used
- **Frontend**: Streamlit, Plotly
- **Backend**: FastAPI, Pydantic
- **Data Pipelines**: Apache Airflow
- **AI Models**: OpenAI GPT, Pinecone for vector search
- **Storage**: AWS S3
- **Database**: Snowflake


### Acknowledgments
OpenAI for GPT models
Pinecone for vector search
Streamlit for the interactive UI
Apache Airflow for workflow orchestration
