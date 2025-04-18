# Venture Scope

Venture Scope is a comprehensive business intelligence platform designed to help entrepreneurs and businesses make data-driven decisions about market opportunities, location intelligence, and competitor analysis. The platform integrates advanced analytics, machine learning, and natural language processing to provide actionable insights.

## Features

- **Market Analysis**: Gain insights into market trends, consumer behavior, and growth opportunities.
- **Location Intelligence**: Identify optimal business locations based on demographics, competition, and other factors.
- **Competitor Analysis**: Understand competitors' strengths and weaknesses to develop effective strategies.
- **Q&A Chatbot**: Ask questions about your business analysis and get personalized answers.
- **Expert Chat**: Interact with virtual representations of industry experts for advice and insights.

## Project Structure
├── airflow/          # Airflow DAGs and services for orchestrating data pipelines
├── backend/          # FastAPI-based backend APIs and external service integrations
├── features/         # Core business logic, AI agents, and decision-making workflows
├── frontend/         # Streamlit-based user interface for interacting with the platform
├── prototype/        # Experimental features, sandbox agents, and research code
└── services/         # Shared utility modules (e.g., S3, Pinecone, embeddings, OCR)
 
## Getting Started

### Prerequisites

- Python 3.8+
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