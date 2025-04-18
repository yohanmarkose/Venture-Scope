import streamlit as st
import pandas as pd
import time, os
import requests
import json
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import uuid
from dotenv import load_dotenv

load_dotenv()

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
</style>
""", unsafe_allow_html=True)

# API endpoint
API_URL = f"{os.getenv('API_URL', 'http://localhost:8000')}"

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

def create_location_map(locations):
    """Create a map visualization of locations based on mockup"""
    if not locations:
        return None
    
    # Create map data
    map_data = []
    for loc in locations:
        # Mock coordinates - in production you would get real geocoding
        if "Boston" in f"{loc.get('city')}, {loc.get('state')}":
            lat, lon = 42.3601, -71.0589
        elif "Chicago" in f"{loc.get('city')}, {loc.get('state')}":
            lat, lon = 41.8781, -87.6298
        elif "Manhattan" in f"{loc.get('city')}, {loc.get('state')}":
            lat, lon = 40.7831, -73.9712
        elif "New York" in f"{loc.get('city')}, {loc.get('state')}":
            lat, lon = 40.7128, -74.0060
        else:
            # Default to center of US if no match
            lat, lon = 37.0902, -95.7129
        
        map_data.append({
            "location": f"{loc.get('area')}, {loc.get('city')}, {loc.get('state')}",
            "lat": lat,
            "lon": lon,
            "suitability": loc.get('suitability_score', 5)
        })
    
    if not map_data:
        return None
    
    map_df = pd.DataFrame(map_data)
    
    # Create a map in the style of your mockup
    fig = px.scatter_mapbox(
        map_df,
        lat="lat",
        lon="lon",
        size="suitability",
        color="suitability",
        color_continuous_scale=["#94a3b8", "#3b82f6", "#1d4ed8"],
        size_max=20,
        hover_name="location",
        zoom=5,
        mapbox_style="carto-positron"
    )
    
    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        height=400,
        coloraxis_colorbar=dict(
            title="Suitability",
            tickvals=[min(map_df.suitability), max(map_df.suitability)],
            ticktext=["Low", "High"]
        )
    )
    
    return fig

def display_locations(locations):
    """Display the location intelligence results styled according to the mockup"""
    if not locations:
        st.warning("No location data available. Please try adjusting your search criteria.")
        return
        
    # Display recommended locations
    st.markdown('<div class="section-header">Recommended Locations</div>', unsafe_allow_html=True)
    
    # Sort locations by suitability score (highest first)
    sorted_locations = sorted(locations, key=lambda x: x.get('suitability_score', 0), reverse=True)
    
    # Display each location card (styled like the mockup)
    for i, location in enumerate(sorted_locations):
        location_name = f"{location.get('area')}, {location.get('city')}, {location.get('state')}"
        trophy = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "📍"
        
        with st.expander(f"{trophy} {location_name} - Score: {location.get('suitability_score')}/10"):
            cols = st.columns([7, 5])
            
            with cols[0]:
                st.markdown("<div style='font-weight:600; margin-bottom:12px;'>Location Profile</div>", unsafe_allow_html=True)
                
                # Profile table like in mockup
                st.markdown(f"""
                <table class="profile-table">
                    <tr>
                        <td>Population Density:</td>
                        <td>{location.get('population_density', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td>Cost of Living:</td>
                        <td>{location.get('cost_of_living', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td>Business Climate:</td>
                        <td>{location.get('business_climate', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td>Quality of Life:</td>
                        <td>{location.get('quality_of_life', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td>Infrastructure:</td>
                        <td>{location.get('infrastructure', 'N/A')}</td>
                    </tr>
                </table>
                """, unsafe_allow_html=True)
                
                # Advantages and challenges
                adv_col, chal_col = st.columns(2)
                
                with adv_col:
                    st.markdown("<div style='font-weight:600; margin-bottom:8px;'>Advantages</div>", unsafe_allow_html=True)
                    for adv in location.get('advantages', []):
                        st.markdown(f"""
                        <div class="advantage-item">
                            <span class="advantage-icon">✓</span>
                            <span>{adv}</span>
                        </div>
                        """, unsafe_allow_html=True)
                
                with chal_col:
                    st.markdown("<div style='font-weight:600; margin-bottom:8px;'>Challenges</div>", unsafe_allow_html=True)
                    for chal in location.get('challenges', []):
                        st.markdown(f"""
                        <div class="challenge-item">
                            <span class="challenge-icon">⚠️</span>
                            <span>{chal}</span>
                        </div>
                        """, unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown("<div style='font-weight:600; margin-bottom:12px; text-align:center;'>Suitability Analysis</div>", unsafe_allow_html=True)
                
                # Create suitability score gauge exactly like mockup
                fig_suitability = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = location.get('suitability_score', 0),
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    number = {'font': {'size': 44, 'color': '#475569'}},
                    title = {'text': "Suitability Score", 'font': {'size': 14, 'color': '#64748b'}},
                    gauge = {
                        'axis': {'range': [0, 10], 'tickwidth': 1, 'tickfont': {'size': 12}},
                        'bar': {'color': "#3b82f6", 'thickness': 0.6},
                        'steps': [
                            {'range': [0, 2], 'color': "#fef9c3"},
                            {'range': [2, 4], 'color': "#fef9c3"},
                            {'range': [4, 6], 'color': "#bfdbfe"},
                            {'range': [6, 8], 'color': "#bfdbfe"},
                            {'range': [8, 10], 'color': "#bbf7d0"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 2},
                            'thickness': 0.6,
                            'value': 7
                        }
                    }
                ))
                
                fig_suitability.update_layout(
                    height=200, 
                    margin=dict(l=30, r=30, t=50, b=20),
                    annotations=[
                        dict(
                            x=0.5,
                            y=0.1,
                            text=f"{location.get('suitability_score', 0)}",
                            font=dict(size=44, color="#475569"),
                            showarrow=False
                        )
                    ],
                    showlegend=False,
                )
                fig_suitability.data[0].mode = "gauge"
                st.plotly_chart(fig_suitability, use_container_width=True, key=f"suitability_{i}")

                st.markdown("<div style='font-weight:600; margin-bottom:12px; text-align:center;'>Risk Analysis</div>", unsafe_allow_html=True)
                
                # Create risk score gauge
                fig_risk = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = location.get('risk_score', 0),
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    number = {'font': {'size': 44, 'color': '#475569'}},
                    title = {'text': "Risk Score", 'font': {'size': 14, 'color': '#64748b'}},
                    gauge = {
                        'axis': {'range': [0, 10], 'tickwidth': 1, 'tickfont': {'size': 12}},
                        'bar': {'color': "#ef4444", 'thickness': 0.6},
                        'steps': [
                            {'range': [0, 2], 'color': "#bbf7d0"},
                            {'range': [2, 4], 'color': "#bbf7d0"},
                            {'range': [4, 6], 'color': "#fef9c3"},
                            {'range': [6, 8], 'color': "#fef9c3"},
                            {'range': [8, 10], 'color': "#fee2e2"}
                        ],
                        'threshold': {
                            'line': {'color': "green", 'width': 2},
                            'thickness': 0.6,
                            'value': 3
                        }
                    }
                ))
                
                fig_risk.update_layout(
                    height=200, 
                    margin=dict(l=30, r=30, t=50, b=20),
                    annotations=[
                        dict(
                            x=0.5,
                            y=0.1,
                            text=f"{location.get('risk_score', 0)}",
                            font=dict(size=44, color="#475569"),
                            showarrow=False
                        )
                    ],
                    showlegend=False
                )
                
                fig_risk.data[0].mode = "gauge"
                st.plotly_chart(fig_risk, use_container_width=True, key=f"risk_{i}")

def display_competitors(competitors):
    """Display the competitors data in a production-grade UI"""
    if not competitors:
        st.warning("No competitor data available.")
        return
    
    st.markdown('<div class="section-header">Competitive Landscape</div>', unsafe_allow_html=True)
    
    # Display in a grid layout
    cols = st.columns(2)
    
    # Sort competitors by some relevant metric
    sorted_competitors = sorted(
        competitors, 
        key=lambda x: (x.get('growth_score', 0) + x.get('customer_satisfaction_score', 0)), 
        reverse=True
    )
    
    # Display each competitor in a card
    for i, comp in enumerate(sorted_competitors):
        with cols[i % 2].expander(f"🏢 {comp.get('name')}"):
            st.markdown(f"""
            <div style="margin-bottom:16px;">
                <div style="font-weight:600; margin-bottom:8px;">Company Overview</div>
                <table style="width:100%;">
                    <tr>
                        <td style="padding:4px 0; width:40%"><strong>Industry:</strong></td>
                        <td>{comp.get('industry', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding:4px 0"><strong>Size:</strong></td>
                        <td>{comp.get('size', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding:4px 0"><strong>Address:</strong></td>
                        <td>{comp.get('address', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding:4px 0"><strong>Revenue:</strong></td>
                        <td>{comp.get('revenue', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding:4px 0"><strong>Market Share:</strong></td>
                        <td>{comp.get('market_share', 'N/A')}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
            # Key metrics
            metrics = st.columns(3)
            with metrics[0]:
                st.metric("Growth Score", f"{comp.get('growth_score', 'N/A')}/10")
            with metrics[1]:
                st.metric("Satisfaction", f"{comp.get('customer_satisfaction_score', 'N/A')}/10")
            with metrics[2]:
                st.metric("Rating", f"{comp.get('rating', 'N/A')}")
            
            # USP
            st.markdown(f"""
            <div class="alert alert-info">
                <div style="font-weight:600; margin-bottom:4px;">Unique Selling Proposition</div>
                <p>{comp.get('unique_selling_proposition', 'No information available')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Reviews
            if comp.get('reviews'):
                st.markdown('<div style="font-weight:600; margin-bottom:8px;">Customer Reviews</div>', unsafe_allow_html=True)
                for review in comp.get('reviews', []):
                    st.markdown(f"""
                    <div style="background-color:#f8fafc; padding:10px; border-radius:6px; margin-bottom:8px;">
                        💬 {review}
                    </div>
                    """, unsafe_allow_html=True)

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
    
    new_product = st.sidebar.text_input("Add a service/product:")
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        if st.button("Add Services/Product", key="add_product", use_container_width=True):
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
    
    size_dict = {"Small": "small", "Medium": "medium", "Large": "large"}
    size = st.sidebar.selectbox("What is the size of business?", 
                             ["Small", "Medium", "Large"])
    size = size_dict.get(size, "large")
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
                <div class="alert alert-info" style="text-align:center;">
                    <div style="font-size:24px; margin-bottom:12px;">🔍 Analyzing Your Business</div>
                    <p>We're processing your request. This typically takes 30-60 seconds.</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Call the API
            api_calls = [
                ("market_analysis", "market_analysis", data),
                ("location_intelligence", "location_intelligence", data)

            ]
            
            with st.spinner():
                api_results = run_async_calls(api_calls)
                st.session_state.api_results = api_results
            
            # Remove loading message
            placeholder.empty()
            
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
        location_data = st.session_state.api_results.get("location_intelligence", {})
        
        # if "error" in location_data:
        #     st.error(f"Error retrieving data: {location_data['error']}")
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
            market_analysis, location_intelligence, qa_tab, chat_with_experience = st.tabs([
                "📊 Market Analysis", 
                "🗺️ Location Intelligence",
                "⁉️ Q & A",
                "💬 Chat with Experience"
            ])
            
            with market_analysis:
                st.markdown('<div class="section-header">Market Overview</div>', unsafe_allow_html=True)
                fig = go.Figure(json.loads(market_data.get("plot")))
                st.header(f"Market Analysis For {market_data.get('industry', '').title()} Industry")
                # Download the markdown
                st.markdown(f"[Download Market Analysis]({market_data.get('file_path')})")
                
                st.plotly_chart(fig)
                st.markdown(market_data.get("answer"))
                    
            with location_intelligence:
                if "locations" in location_data:
                    display_locations(location_data.get("locations", []))
                else:
                    st.warning("No location data available.")
                if "competitors" in location_data:
                    display_competitors(location_data.get("competitors", []))
                else:
                    st.warning("No competitor data available.")
            
            with chat_with_experience:
                st.markdown('<div class="section-header">💬 Chat with Industry Experts - Ask them about their stories</div>', unsafe_allow_html=True)

                experts = [
                    {
                        "name": "Ben Horowitz",
                        "img": "https://pdfparserdataset.s3.us-east-2.amazonaws.com/chatbot_source_books/BenHorowitz/benhorowitz.png",
                        "bio": "Co-founder of Andreessen Horowitz. Pioneer in venture capital with deep expertise in tech entrepreneurship and startup leadership.",
                        "key": "BenHorowitz",
                        "base_info": "You are Ben Horowitz — co-founder of Andreessen Horowitz and one of Silicon Valley's most respected voices on entrepreneurship, leadership, and culture in high-growth startups. You respond with directness, candor, and personal insight drawn from years of experience building and backing companies. Your tone is authentic, no-nonsense, and occasionally humorous or anecdotal — especially when discussing hard truths of startup life.",
                    },
                    {
                        "name": "Mark Cuban",
                        "img": "https://pdfparserdataset.s3.us-east-2.amazonaws.com/chatbot_source_books/MarkCuban/MarkCuban.png",
                        "bio": "Billionaire entrepreneur and investor. Owner of the Dallas Mavericks with distinctive perspectives on business innovation and growth.",
                        "key": "MarkCuban",
                        "base_info": "You are Mark Cuban — self-made billionaire, media personality, and sharp-tongued investor known for speaking his mind. As owner of the Dallas Mavericks and one of the most vocal sharks on *Shark Tank*, you combine tech-savvy thinking with real-world grit. Your style is blunt, confident, and relentless, always pushing entrepreneurs to know their numbers, grind harder, and outwork everyone in the room."
                    },
                    {
                        "name": "Reed Hastings",
                        "img": "https://pdfparserdataset.s3.us-east-2.amazonaws.com/chatbot_source_books/ReedHastings/ReedHastings.webp",
                        "bio": "Co-founder of Netflix. Visionary in technology and organizational culture with expertise in scaling consumer-focused platforms.",
                        "key": "ReedHastings",
                        "base_info": "You are Reed Hastings — co-founder of Netflix and a pioneer in using technology and company culture to scale consumer platforms. Your insights are grounded in experimentation, data, and empowering people. You speak with calm precision, emphasizing vision, discipline, and innovation over hype.",
                    },
                    {
                        "name": "Sam Walton",
                        "img": "https://pdfparserdataset.s3.us-east-2.amazonaws.com/chatbot_source_books/SamWalton/SamWalton.png",
                        "bio": "Founder of Walmart. Retail innovator who revolutionized American commerce through strategic expansion and operational excellence.",
                        "key": "SamWalton",
                        "base_info": "You are Sam Walton — founder of Walmart and a visionary in American retail. You built an empire on principles of low prices, customer satisfaction, rural expansion, and operational excellence. You speak plainly and practically, often emphasizing hard work, frugality, and putting the customer first. Your tone is humble, folksy, and grounded in real-world business experience, often enriched with anecdotes from building Walmart from the ground up."
                    }
                ]

                if 'selected_expert' not in st.session_state:
                    st.session_state.selected_expert = None
                if 'expertchat_history' not in st.session_state:
                    st.session_state.expertchat_history = []

                # Display expert cards
                cols = st.columns(4)
                for i, expert in enumerate(experts):
                    with cols[i]:
                        # Start the card container
                        st.markdown(f"""
                            <div style="text-align:center; padding:20px; background-color:#f9fafb; border-radius:16px; box-shadow:0 2px 8px rgba(0,0,0,0.05); height:100%; display:flex; flex-direction:column; justify-content:space-between;">
                                <div>
                                    <img src="{expert['img']}" alt="{expert['name']}" style="border-radius:50%; width:90px; height:90px; object-fit:cover; margin-bottom:10px;" />
                                    <div style="font-weight:600; font-size:16px; margin-top:5px;">{expert['name']}</div>
                                    <p style="font-size:13px; color:#555; min-height:80px;">{expert['bio']}</p>
                                </div>
                        """, unsafe_allow_html=True)
                        
                        # Add button container within the card
                        st.markdown('<div style="margin-top:10px;">', unsafe_allow_html=True)
                        
                        # Insert the Streamlit button
                        if st.button("Chat", key=f"chat_{expert['key']}", use_container_width=True):
                            st.session_state.selected_expert = expert
                            st.session_state.expertchat_history = []

                        st.markdown("</div>", unsafe_allow_html=True)

                # Chat section
                if st.session_state.selected_expert:
                    expert = st.session_state.selected_expert
                    st.markdown(f"<hr><h4>🧠 Chat with {expert['name']}</h4>", unsafe_allow_html=True)

                    with st.form("expert_chat_form", clear_on_submit=True):
                        expert_question = st.text_input("Ask a question:", key="expert_user_input")
                        send_button = st.form_submit_button("Send")

                        if send_button and expert_question:
                            payload = {
                                "expert_key": expert["key"],
                                "question": expert_question,
                                "base_info": expert["base_info"],
                                "model": "gpt-4.o-mini"
                            }

                            with st.spinner("Thinking..."):
                                try:
                                    res = requests.post(f"{API_URL}/chat_with_expert", json=payload)
                                    if res.status_code == 200:
                                        answer = res.json()["answer"]
                                        st.session_state.expertchat_history.append({"expert": expert["name"],"question": expert_question,"answer": answer})
                                        st.success(answer)
                                    else:
                                        st.error(f"❌ {res.status_code}: {res.text}")
                                except Exception as e:
                                    st.error(f"API error: {str(e)}")

                    # Show chat history
                    if st.session_state.expertchat_history:
                        st.markdown("### 💬 Chat History")
                        for chat in st.session_state.expertchat_history[::-1]:
                            st.markdown(f"🧠 **{chat['expert']}**")
                            st.markdown(f"**Q:** {chat['question']}")
                            st.markdown(f"**A:** {chat['answer']}")
                            st.markdown("---")


            with qa_tab:
                st.markdown('<div class="section-header">Q & A</div>', unsafe_allow_html=True)                
                st.markdown("Ask questions about your business analysis and get personalized answers based on the generated reports.")

                chat_container = st.container()
                
                # Display chat history
                with chat_container:
                    for chat in st.session_state.chat_history_display:
                        if chat["role"] == "user":
                            st.markdown(f"""
                            <div class="chat-message user-message" style="background-color: #FFE4C4; padding: 10px; border-radius: 5px; margin-bottom: 10px; color: #000000;">
                                <div><strong>You:</strong></div>
                                <div>{chat["content"]}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="chat-message bot-message" style="background-color: #F5F5DC; padding: 10px; border-radius: 5px; margin-bottom: 10px; color: #000000;">
                                <div><strong>Assistant:</strong></div>
                                <div>{chat["content"]}</div>
                            </div>
                            """, unsafe_allow_html=True)

                user_question = st.text_input("Ask a question about your business:", placeholder="e.g., What are the main competitors in this industry?")

                if st.button("Ask") and user_question:
                    st.session_state.chat_history_display.append({"role": "user", "content": user_question})
                    
                    message_history = []
                    for msg in st.session_state.chat_history_display:
                        message_history.append({
                            "type": "human" if msg["role"] == "user" else "ai", 
                            "content": msg["content"]
                        })
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
                            response = requests.post(
                                f"{API_URL}/q_and_a",
                                json=qa_data
                            )
                            
                            if response.status_code == 200:
                                answer = response.json().get("answer", "Sorry, I couldn't process your request.")
                                st.session_state.chat_history_display.append({"role": "assistant", "content": answer})
                                st.rerun()
                            else:
                                st.error(f"Error: {response.status_code} - {response.text}")
                        except Exception as e:
                            st.error(f"Error processing request: {str(e)}")
                            import traceback
                            st.error(traceback.format_exc())
                    
            
            # Add a button to start a new analysis
            # if st.button("Start New Analysis", type="primary", use_container_width=True):
            #     st.session_state.submitted = False
            #     st.session_state.api_results = None
            #     st.session_state.products = []
            #     st.session_state.chat_history_display = []
            #     message_history = []
            #     st.rerun()
    
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

    # Footer
    st.markdown("""
    <div class="footer">
        <p>Venture Scope | Business Location Intelligence Platform</p>
        <p>© 2025 All Rights Reserved</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
