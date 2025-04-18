# 🚀 Venture Scope: AI-Powered Startup Advisory Platform

## Introduction

Every day, promising businesses fail not because of bad products but because they launched in the wrong place at the wrong time. While corporations leverage teams of analysts before making decisions, most entrepreneurs are forced to rely on gut feelings and incomplete market information. This knowledge gap creates an uneven playing field, where great ideas fail simply because their founders couldn't access critical market intelligence.

Venture Scope aims to democratize business intelligence by creating an AI advisory platform that translates complex market data into actionable insights. By analyzing location dynamics, competitor landscapes, regulatory environments, and industry trends, we'll give entrepreneurs the same strategic advantages previously available only to resource-rich corporations—turning entrepreneurial guesswork into informed strategy.

## Project Overview

To create a comprehensive startup advisory system, the project will integrate data from CrunchBase, Yahoo Finance, real estate databases, e-commerce analytics, and government policy documents. The platform will analyze business domains, company size parameters, and location preferences to generate tailored recommendations and insights. Deliverables include a functional data pipeline for data ingestion, analytical models for AI-driven business analysis, and an interactive dashboard for seamless user experience.

### Stakeholders

- Entrepreneurs and business founders
- Small business development centers
- Business incubators and accelerators
- Venture capital firms and angel investors
- Economic development organizations

## Resources

Google Codelab: [Codelab](https://codelabs-preview.appspot.com/?file_id=1N4bKPKzBa_0oUqOuSj-WLyxeYnQDBJX74bt5igdLZYM/edit?tab=t.0#4)

Google Docs: [Project Document](https://docs.google.com/document/d/1N4bKPKzBa_0oUqOuSj-WLyxeYnQDBJX74bt5igdLZYM/edit?usp=sharing)

## Problem Statement:

### Current Challenges

- Fragmented market intelligence requiring consultation from multiple sources
- Difficulty in assessing location-specific business advantages
- Time-consuming regulatory research across different states
- Limited access to competitor performance metrics
- Inadequate tools for cross-referencing market trends with real estate costs

### Opportunities
- Streamline the startup planning process by providing consolidated insights
- Reduce business failure rates through data-driven location, consumer, and market selection
- Enable more agile business planning with comprehensive, on-demand analytics
- Democratize access to premium business intelligence
- Facilitate economic development by identifying growth opportunities

## Team Members

- Vedant Mane
- Abhinav Gangurde
- Yohan Markose

## Attestation:

WE ATTEST THAT WE HAVEN’T USED ANY OTHER STUDENTS’ WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK

## Methodologies

### Data Sources:

#### Structured Datasets : (Snowflake)

1. CrunchBase Data
- Funding rounds for public and private equity firms
- Company demographics, founding dates, growth trajectories
- Acquisition data and valuation trends

2. US Real Estate Databases
- Commercial property costs by location
- Rental rate trends for business spaces
- Property availability metrics

3. Ecommerce Analytics
- Product demand patterns from major platforms
- Consumer behavior analytics
- Market penetration statistics

#### **Structured Datasets : (API)**

1. Yahoo Finance API & Alpha Vantage API
- Market performance indicators
- Public company financial metrics
- Industry growth projections
  
#### Unstructured Datasets : (PDF and Websites)

1. Y-Combinator library and Venture Capital Research Reports 
- Rich source of founder advice and startup methodologies
- Testimonials from industry leaders 
- VC reports - expert insights about market trends and investment criteria

2. Government Policy Documents
- State-by-state business regulations
- Tax incentive programs
- Licensing requirements

### Technologies and Tools:

- **Frontend:** Streamlit
- **Backend API:** FastAPI
- **Hosted APIs:** Google Cloud Run
- **Workflow Orchestration:** Apache Airflow
- **Cloud Storage:** AWS S3
- **Data Warehouse:** Snowflake
- **Vector Database:** Pinecone Vector DB
- **Document Processing:** Mistral OCR
- **LLM Management:** LiteLLM
- **ML Models:** Huggingface (Image Generation)
- **AI Integration:** OpenAI / XAI Grok
- **Context Management:** Model Context Protocol from Anthropic
- **Workflow Management:** Langgraph
- **Multi-Agent Framework:** Crew AI / Smolagents


### Data Pipeline Design:

1. Data Ingestion
- API connectors for CrunchBase, Yahoo Finance, and Alpha Vantage
- Web scrapers for real estate data
- PDF parsers for government policy documents using Mistral OCR
- E-commerce analytics integration

2. Data Storage
- Raw data lake in AWS S3
- Processed data in Snowflake data warehouse
- Vector embeddings in Pinecone for semantic search

3. Data Processing
- Airflow-orchestrated ETL pipelines
- Document processing with Mistral OCR
- Vector embeddings generation for unstructured data

4. Analytics Layer
- LLM-powered analysis using LiteLLM and OpenAI API
- Multi-agent processing with Crew AI
- Workflow orchestration via Langgraph

### Data Processing and Transformation:

#### Structured Data Processing (Snowflake)

1. Column Selection and Table Consolidation
- SQL transformations to extract only relevant columns from raw tables in Snowflake
- Create optimized views joining related data across multiple source tables
- Rename columns for consistency

2. Data Cleaning and Type Conversion
- Identify and handle null values that would disrupt the data
- Convert data types to ensure consistency
- Remove duplicates data that could affect the analysis

3. Custom Metrics Creation
- Derive new columns for company financial health indicators from Yahoo Finance data
- Calculate growth metrics and  market capitalizations using Alpha Vantage API

#### Unstructured Data Processing (PDF)

1. Vector DB for State level Government and Business Policy Documents
- Use Mistral OCR to convert PDF documents to markdown format
- Generate embeddings for document chunks using Open AI embedding models
- Store embeddings in Pinecone with relevant metadata for efficient retrieval and filtering

2. Y-Coordinator (website)
- Creating a custom scraping  workflow to collect relevant data and testimonials

### Proof of Concept

- Created custom MCP servers for testing usability
- Created a custom MCP client using python sdk and connected to the created server
- Tested tool calling capability between the created MCP client and server
- Tested Langgraph and MCP integration using newly built langchain_mcp_adaptor package
- Collected relevant data sources and segregated a plan for their utilization


## Project Plan and Timeline

### Milestones and Deliverables:

- Project Initialization & Data Collection (Days 1-3)
  - Project requirements documentation
  - Data source access configuration (Snowflake, Yahoo Finance)
  - AWS infrastructure setup with pre-configured templates
  - Initial data collection from Snowflake and API and identified unstructured data sources
  - Prototyping and workflow configurability checks with the selected tools sets

- Core System Development (Days 4-7)
  - Streamlined Snowflake schema implementation - harmonize the structured unstructured datasets
  - Pinecone vector database configuration and document processing
  - FastAPI backend development with minimal viable endpoints
  - Basic streamlit dashboard framework for UI workflow for the application

- Analytics & Integration (Days 8-10)
  - LLM integration with simplified prompt templates
  - Limited-scope multi-agent framework implementation and prototyping
  - Integration of critical data sources and web search modules in the multi-agentic framework
  - Focused regulatory analysis for top 10 business-friendly states and 5 business domains

- Testing & Deployment (Days 11-14)
  - Deployment and testing the workflow for any bugs and updatation
  - Documentation of core functionality
  - Project documentation, presentation and demonstration

### Estimated Workflow Timeline: 
- Project Start: April 5, 2025
- Data Integration: April 8, 2025
- Core System Functionality: April 11, 2025
- Analytics Layer: April 14, 2025
- Agentic Architecture & Deployment: April 17, 2025
- Project Documentation: April 18, 2025
- Project Presentation & Demonstration: April 19, 2025

## Resources and Team:

### Team-Workload Segregation :

| Team Member | Contribution |
|-------------|-------------|
| Abhinav Gangurde | • Handle data pipeline orchestration using Apache Airflow<br>• Develop and maintain AWS S3 data staging capabilities<br>• Deploy the application using Docker & Docker Compose on the Google Cloud Infrastructure<br>• Prototype and develop MCP integration with Google Maps for the Location Intelligence Tool |
| Vedant Mane | • Handle OCR processing of regulatory documents<br>• Implement Pinecone vector embeddings for semantic search<br>• Develop the Streamlit frontend dashboard<br>• Create FastAPI backend endpoints<br>• Configure LLM integrations via LiteLLM and OpenAI API |
| Yohan Markose | • Implement Snowflake integrations and data infrastructure<br>• Implement Agentic Architecture using Langgraph<br>• Implement Tavily for Web Search Integration Tool<br>• Develop and implement graphs and charts for data visualizations |

## Risks and Mitigation Strategies:

### MCP Integration and Deployment

- Risks : Integration with GoogleMaps and Langgraph and overall workflow integration with application
- Mitigation : Protype the workflow and allocate sufficient time in the development cycle.

### MCP Integration with Langgraph

- Risks : Integration with Langgraph in binding MCP servers and tools with langgraph agent and workflow
- Mitigation : Protype the workflow, isolate MCP from langgraph agents if needed

### Project Management

- Risks: With a 14 days timeline for the application deliver workload and functionalities may need to be reviewed
- Mitigation : Establish a daily checkpoint meetings like scrum to quickly address blockers and discuss on the potential solution

## Expected Outcomes and Benefits:

### Measurable Goals
- Reduces business research time compared to manual methods
- Accurate in market trend predictions
- Process regulatory data from all 50 states with regulatory document processing
- Provide insights into business domains through Pinecone Vector Search

### Expected Benefits
- Enable data-driven decision-making, especially for small and medium-scale businesses with limited resources
- Reduce startup failure rates through optimized location, market selection, and target customer identification
- Accelerate business launch timelines with comprehensive, on-demand insights
- Democratize access to high-quality business intelligence
- Identify underserved markets and business opportunities
- Facilitate economic development in emerging business sectors

## Conclusion

Venture Scope isn't just another analytics platform—it's a business equalizer. By combining cutting-edge AI technologies with comprehensive market data, we're creating a strategic advantage that was previously available only to corporate giants. Our solution will transform how entrepreneurs evaluate opportunities, select locations, and understand market dynamics, all through an intuitive interface delivering actionable insights in minutes rather than months. With a focused two-week development sprint led by our specialized team, we'll deliver an MVP that demonstrates immediate value while establishing the foundation for ongoing evolution. Venture Scope represents not just a tool but a fundamental shift in how business decisions are made – turning entrepreneurial intuition into data-driven confidence and leveling the playing field for innovators everywhere.

