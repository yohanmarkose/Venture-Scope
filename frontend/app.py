import streamlit as st
import pandas as pd
import time
import requests
import json
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import uuid

# Set page configuration
st.set_page_config(
    page_title="Venture Scope | Business Location Intelligence",
    page_icon="🌎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling to match mockups
st.markdown("""
<style>
    /* Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4, h5 {
        font-weight: 600;
    }
    
    /* Tabs styling to match mockup */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        border-bottom: 1px solid #e2e8f0;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 10px 16px;
        border: none;
        background-color: transparent;
        border-radius: 0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: transparent !important;
        border-bottom: 2px solid #6366F1 !important;
        font-weight: 600;
    }
    
    /* Location card styling */
    .location-card {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 16px;
    }
    
    .location-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #f8fafc;
        padding: 12px 16px;
        border-bottom: 1px solid #e2e8f0;
    }
    
    .location-card-body {
        padding: 16px;
    }
    
    /* Location profile table */
    .profile-table {
        width: 100%;
        border-collapse: collapse;
    }
    
    .profile-table tr {
        border-bottom: 1px solid #e2e8f0;
    }
    
    .profile-table tr:last-child {
        border-bottom: none;
    }
    
    .profile-table td {
        padding: 10px 0;
    }
    
    .profile-table td:first-child {
        font-weight: 500;
        width: 40%;
    }
    
    /* Advantages and challenges */
    .advantage-item {
        display: flex;
        align-items: flex-start;
        margin-bottom: 8px;
    }
    
    .advantage-icon {
        margin-right: 8px;
        color: #10b981;
    }
    
    .challenge-item {
        display: flex;
        align-items: flex-start;
        margin-bottom: 8px;
    }
    
    .challenge-icon {
        margin-right: 8px;
        color: #f59e0b;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid #e2e8f0;
    }
    
    /* Map container */
    .map-container {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 20px;
    }
    
    /* Footer */
    .footer {
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #e2e8f0;
        text-align: center;
        font-size: 0.875rem;
        color: #64748b;
    }
    
    /* Alert/info boxes */
    .alert {
        padding: 16px;
        border-radius: 6px;
        margin-bottom: 16px;
    }
    
    .alert-info {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
    }
    
    .alert-success {
        background-color: #f0fdf4;
        border-left: 4px solid #10b981;
    }
    
    .alert-warning {
        background-color: #fffbeb;
        border-left: 4px solid #f59e0b;
    }
    
    .alert-error {
        background-color: #fef2f2;
        border-left: 4px solid #ef4444;
    }
    
    /* Remove Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .reportview-container .main footer {visibility: hidden;}
    
    /* Chat styling */
    .chat-message {
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
        color: #111827; /* Dark text color for all messages */
    }
    
    .user-message {
        background-color: #e2e8f0;
        border-top-right-radius: 2px;
        margin-left: 25%;
    }
    
    .bot-message {
        background-color: #f1f5f9;
        border-top-left-radius: 2px;
        margin-right: 25%;
    }
    
    /* Ensure chat text has good contrast */
    .chat-message strong {
        color: #111827; /* Dark color for names */
    }
    
    .chat-message div {
        color: #111827; /* Dark color for content */
    }
</style>
""", unsafe_allow_html=True)

# API endpoint
API_URL = "http://localhost:8000"

@st.cache_data
def load_cities():
    try:
        df = pd.read_csv("frontend/uscities.csv")
        df['city_state'] = df['city'] + ", " + df['state_name']
        return df['city_state'].dropna().unique()
    except Exception as e:
        st.warning(f"Could not load cities data: {e}")
        # Return a limited set as fallback
        return ["New York, New York", "Chicago, Illinois", "Boston, Massachusetts"]

@st.cache_data
def load_industries():
    industries = [
        "Education & Training",
        "Finance & Insurance",
        "Healthcare & Life Sciences",
        "Information Technology & Software",
        "Manufacturing & Industrial",
        "Media & Entertainment",
        "Professional Services",
        "Public Sector & Nonprofit",
        "Retail & Consumer Goods",
        "Transportation & Logistics"
    ]
    return industries

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

def main():
    # Page title
    st.title("Venture Scope Dashboard")
    
    # Initialize session state
    if "products" not in st.session_state:
        st.session_state.products = []
    if "api_results" not in st.session_state:
        st.session_state.api_results = None
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "chatbot_session_id" not in st.session_state:
        st.session_state.chatbot_session_id = str(uuid.uuid4())
    if "chat_history_display" not in st.session_state:
        st.session_state.chat_history_display = []
    
    # Sidebar configuration
    st.sidebar.markdown("<div style='font-weight:600; font-size:18px; margin-bottom:16px;'>Business Configuration</div>", unsafe_allow_html=True)
    
    # Load data
    industries = load_industries()
    cities = load_cities()
    
    # Input form in sidebar
    selected_industry = st.sidebar.selectbox("Select Business Domain", industries)
    selected_city = st.sidebar.multiselect("Ideal Business Location", sorted(cities))
    budget_range = st.sidebar.slider("Select Budget Range", 
                                   10000, 1000000, (100000, 500000), 
                                   format="$%d")
    
    # Product configuration
    st.sidebar.markdown("<div style='font-weight:600; font-size:18px; margin-top:24px; margin-bottom:16px;'>Product Configuration</div>", unsafe_allow_html=True)
    
    new_product = st.sidebar.text_input("Add a product:")
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        if st.button("Add Product", key="add_product", use_container_width=True):
            if new_product and new_product not in st.session_state.products:
                st.session_state.products.append(new_product)
                st.rerun()
    
    with col2:
        if st.button("Clear", key="clear_products"):
            st.session_state.products = []
            st.rerun()
    
    # Display products list
    if st.session_state.products:
        st.sidebar.markdown("<div style='font-weight:500; margin-top:12px;'>Your Products:</div>", unsafe_allow_html=True)
        for i, product in enumerate(st.session_state.products):
            cols = st.sidebar.columns([4, 1])
            cols[0].markdown(f"- {product}")
            if cols[1].button("❌", key=f"remove_{i}"):
                st.session_state.products.remove(product)
                st.rerun()
    
    # Business details
    st.sidebar.markdown("<div style='font-weight:600; font-size:18px; margin-top:24px; margin-bottom:16px;'>Business Details</div>", unsafe_allow_html=True)
    
    size = st.sidebar.selectbox("What is the size of business?", 
                             ["Startup", "Small Enterprise", "Medium Enterprise", "MNC"])
    additional_details = st.sidebar.text_area("What is your Unique Selling Proposition?")
    
    # Submit button
    if st.sidebar.button("Generate Business Intelligence", type="primary", use_container_width=True):
        if len(st.session_state.products) > 0 and selected_city:
            st.session_state.submitted = True
            
            # Create data payload
            data = {
                "industry": selected_industry,
                "product": st.session_state.products,
                "location/city": selected_city,
                "budget": list(budget_range),  # Convert tuple to list for JSON
                "size": size,
                "unique_selling_proposition": additional_details
            }
            
            # Show loading state
            placeholder = st.empty()
            with placeholder:
                st.markdown("""
                <div class="alert alert-info" style="text-align:center; padding:30px;">
                    <div style="font-size:24px; margin-bottom:12px;">🔍 Analyzing Your Business</div>
                    <p>We're processing your request. This typically takes 30-60 seconds.</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Call the API
            api_calls = [
                # ("location_intelligence", "location_intelligence", data)
                ("market_analysis", "market_analysis", data)
                # ("q_and_a", "q_and_a", data)
            ]
            
            with st.spinner():
                api_results = run_async_calls(api_calls)
                st.session_state.api_results = api_results
            
            # Remove loading message
            placeholder.empty()
            
            # Reset chat history on new analysis
            st.session_state.chat_history_display = []
            
            # Force UI refresh
            st.rerun()
            
        else:
            if not st.session_state.products:
                st.sidebar.error("Please add at least one product.")
            if not selected_city:
                st.sidebar.error("Please select at least one location.")
    
    # Display results if available
    if st.session_state.submitted and st.session_state.api_results:
        market_data = st.session_state.api_results.get("market_analysis", {})
        
        if "error" in market_data:
            st.error(f"Error retrieving data: {market_data['error']}")
        else:
            # Display analysis summary
            st.markdown(f"""
            <div class="alert alert-success">
                <div style="font-size:18px; font-weight:600; margin-bottom:8px;">Analysis Complete</div>
                <p>We've analyzed <strong>{selected_industry}</strong> businesses in <strong>{', '.join(selected_city)}</strong> with a budget range of <strong>${budget_range[0]:,} - ${budget_range[1]:,}</strong>.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display tabs that match the mockups
            market_analysis, location_intelligence, market_competition, qa_tab = st.tabs([
                "📊 Market Analysis", 
                "🗺️ Location Intelligence", 
                "🏢 Market Competition",
                "⁉️ Q & A"
            ])
            
            with market_analysis:
                st.markdown('<div class="section-header">Market Overview</div>', unsafe_allow_html=True)
                fig = go.Figure(json.loads(market_data.get("plot")))
                st.header(market_data.get("industry"))
                st.plotly_chart(fig)
                st.markdown(market_data.get("answer"))

            with location_intelligence:
                st.markdown("""
                <div class="alert alert-info" style="text-align:center; padding:20px;">
                    <div style="font-size:18px; margin-bottom:10px;">Location Analysis</div>
                    <p>Location intelligence data is not available in this demo version. In the full application, this tab would show detailed location analysis and recommendations.</p>
                </div>
                """, unsafe_allow_html=True)
                
            with market_competition:
                st.markdown("""
                <div class="alert alert-info" style="text-align:center; padding:20px;">
                    <div style="font-size:18px; margin-bottom:10px;">Competitor Analysis</div>
                    <p>Competitor analysis data is not available in this demo version. In the full application, this tab would show detailed competitive landscape information.</p>
                </div>
                """, unsafe_allow_html=True)

            with qa_tab:
                st.markdown('<div class="section-header">Q & A</div>', unsafe_allow_html=True)
                
                # Add description
                st.markdown("Ask questions about your business analysis and get personalized answers based on the generated reports.")

                chat_container = st.container()
                
                # Display chat history
                with chat_container:
                    for chat in st.session_state.chat_history_display:
                        if chat["role"] == "user":
                            st.markdown(f"""
                            <div class="chat-message user-message">
                                <div><strong>You:</strong></div>
                                <div>{chat["content"]}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="chat-message bot-message">
                                <div><strong>Assistant:</strong></div>
                                <div>{chat["content"]}</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                # Create input for user question
                user_question = st.text_input("Ask a question about your business:", placeholder="e.g., What are the main competitors in this industry?")
                
                # Submit button
                if st.button("Ask") and user_question:
                    # Add user message to display history
                    st.session_state.chat_history_display.append({"role": "user", "content": user_question})
                    
                    # Prepare message history for API call
                    message_history = []
                    # Convert display history to message history format
                    for msg in st.session_state.chat_history_display:
                        message_history.append({
                            "type": "human" if msg["role"] == "user" else "ai", 
                            "content": msg["content"]
                        })
                    
                    # Prepare data for API call
                    qa_data = {
                        "industry": selected_industry,
                        "product": st.session_state.products,
                        "location/city": selected_city,
                        "budget": list(budget_range),  # Convert tuple to list for JSON
                        "size": size,
                        "unique_selling_proposition": additional_details,
                        "question": user_question,
                        "session_id": st.session_state.chatbot_session_id,
                        "message_history": message_history
                    }
                    
                    with st.spinner("Processing your question..."):
                        try:
                            # Make API call to get answer
                            response = requests.post(
                                f"{API_URL}/q_and_a",
                                json=qa_data
                            )
                            
                            if response.status_code == 200:
                                answer = response.json().get("answer", "Sorry, I couldn't process your request.")
                                
                                # Add to display history
                                st.session_state.chat_history_display.append({"role": "assistant", "content": answer})
                                
                                # Force refresh to update the UI
                                st.rerun()
                            else:
                                st.error(f"Error: {response.status_code} - {response.text}")
                        except Exception as e:
                            st.error(f"Error processing request: {str(e)}")
                            import traceback
                            st.error(traceback.format_exc())

            # Add a button to start a new analysis
            if st.button("Start New Analysis", type="primary"):
                st.session_state.submitted = False
                st.session_state.api_results = None
                st.session_state.products = []
                st.session_state.chat_history_display = []
                st.rerun()
    
    # Show welcome screen when not submitted
    elif not st.session_state.submitted:
        st.markdown("""
        <div class="alert alert-info" style="text-align:center; padding:30px;">
            <div style="font-size:24px; font-weight:600; margin-bottom:16px;">Welcome to Venture Scope</div>
            <p style="font-size:16px; margin-bottom:24px;">Make data-driven location decisions for your business with our advanced analytics platform.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Feature showcase
        st.markdown('<div class="section-header">How It Works</div>', unsafe_allow_html=True)
        
        cols = st.columns(3)
        with cols[0]:
            st.markdown("""
            <div style="text-align:center; padding:20px; background-color:#f8fafc; border-radius:8px; height:100%;">
                <div style="font-size:36px; margin-bottom:12px;">📊</div>
                <div style="font-weight:600; margin-bottom:8px;">Market Analysis</div>
                <p style="color:#64748b;">Gain insights into market trends, consumer behavior, and growth opportunities.</p>
            </div>
            """, unsafe_allow_html=True)
            
        with cols[1]:
            st.markdown("""
            <div style="text-align:center; padding:20px; background-color:#f8fafc; border-radius:8px; height:100%;">
                <div style="font-size:36px; margin-bottom:12px;">🗺️</div>
                <div style="font-weight:600; margin-bottom:8px;">Location Intelligence</div>
                <p style="color:#64748b;">Find the perfect location based on multiple factors including demographics and competition.</p>
            </div>
            """, unsafe_allow_html=True)
            
        with cols[2]:
            st.markdown("""
            <div style="text-align:center; padding:20px; background-color:#f8fafc; border-radius:8px; height:100%;">
                <div style="font-size:36px; margin-bottom:12px;">🏢</div>
                <div style="font-weight:600; margin-bottom:8px;">Competitor Analysis</div>
                <p style="color:#64748b;">Understand your competition's strengths and weaknesses to develop effective strategies.</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Page footer
    st.markdown("""
    <div class="footer">
        <p>Venture Scope | Business Location Intelligence Platform</p>
        <p>© 2025 All Rights Reserved</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()