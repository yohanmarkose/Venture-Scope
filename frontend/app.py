import streamlit as st
import pandas as pd
import time
import requests
import json
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

# Set page configuration
st.set_page_config(
    page_title="Venture Scope",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.8rem;
        font-weight: 600;
        color: #0D47A1;
        padding-top: 1rem;
    }
    .card {
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #E3F2FD;
        border-left: 5px solid #1E88E5;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #E8F5E9;
        border-left: 5px solid #4CAF50;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #FFF8E1;
        border-left: 5px solid #FFC107;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #f7f7f7;
        border-radius: 5px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E88E5;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #555;
        margin-top: 0.3rem;
    }
    .list-item {
        margin-bottom: 0.5rem;
        margin-left: 1rem;
        line-height: 1.6;
    }
    .sidebar-header {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #0D47A1;
    }
</style>
""", unsafe_allow_html=True)

# API endpoint
API_URL = "http://localhost:8000"

@st.cache_data
def load_cities():
    df = pd.read_csv("frontend/uscities.csv")
    df['city_state'] = df['city'] + ", " + df['state_name']
    return df['city_state'].dropna().unique()

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

def display_locations(locations):
    """Display the location intelligence results"""
    if not locations:
        return
    
    st.markdown("<div class='subheader'>Recommended Locations</div>", unsafe_allow_html=True)
    
    for i, location in enumerate(locations):
        with st.expander(f"📍 {location.get('area')}, {location.get('city')}, {location.get('state')}"):
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            
            # Metrics row
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class='metric-container'>
                    <div class='metric-value'>{location.get('suitability_score')}/10</div>
                    <div class='metric-label'>Suitability Score</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class='metric-container'>
                    <div class='metric-value'>{location.get('risk_score')}/10</div>
                    <div class='metric-label'>Risk Score</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col3:
                st.markdown(f"""
                <div class='metric-container'>
                    <div class='metric-value'>{location.get('cost_of_living')}</div>
                    <div class='metric-label'>Cost of Living</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Details row
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Area Details")
                st.markdown(f"**Population Density:** {location.get('population_density')}")
                st.markdown(f"**Business Climate:** {location.get('business_climate')}")
                st.markdown(f"**Quality of Life:** {location.get('quality_of_life')}")
                st.markdown(f"**Infrastructure:** {location.get('infrastructure')}")
            
            with col2:
                st.markdown("#### Key Insights")
                st.markdown("<div class='success-box'>", unsafe_allow_html=True)
                st.markdown("##### Advantages")
                for adv in location.get('advantages', []):
                    st.markdown(f"<div class='list-item'>✅ {adv}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<div class='warning-box'>", unsafe_allow_html=True)
                st.markdown("##### Challenges")
                for chal in location.get('challenges', []):
                    st.markdown(f"<div class='list-item'>⚠️ {chal}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

def display_competitors(competitors):
    """Display the market competition results"""
    if not competitors:
        return
    
    st.markdown("<div class='subheader'>Market Competition</div>", unsafe_allow_html=True)
    
    # Create columns for a grid layout
    cols = st.columns(2)
    
    for i, comp in enumerate(competitors):
        with cols[i % 2].expander(f"🏢 {comp.get('name')}"):
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            
            # Basic info
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class='metric-container'>
                    <div class='metric-value'>{comp.get('rating', 'N/A')}</div>
                    <div class='metric-label'>Rating</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("#### Business Details")
                st.markdown(f"**Industry:** {comp.get('industry')}")
                st.markdown(f"**Size:** {comp.get('size')}")
                st.markdown(f"**Revenue:** {comp.get('revenue')}")
                st.markdown(f"**Market Share:** {comp.get('market_share')}")
                
            with col2:
                st.markdown(f"""
                <div class='metric-container' style='margin-bottom: 10px;'>
                    <div class='metric-value'>{comp.get('growth_score')}/10</div>
                    <div class='metric-label'>Growth Score</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class='metric-container'>
                    <div class='metric-value'>{comp.get('customer_satisfaction_score')}/10</div>
                    <div class='metric-label'>Customer Satisfaction</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Address
            st.markdown("#### Location")
            st.markdown(f"📍 {comp.get('address')}")
            
            # USP
            st.markdown("<div class='info-box'>", unsafe_allow_html=True)
            st.markdown("#### Unique Selling Proposition")
            st.markdown(f"{comp.get('unique_selling_proposition')}")
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Reviews
            if comp.get('reviews'):
                st.markdown("#### Customer Reviews")
                for rev in comp.get('reviews', []):
                    st.markdown(f"<div style='background-color:#f9f9f9; padding:10px; border-radius:5px; margin-bottom:8px;'>💬 {rev}</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

def main():
    # Custom header
    st.markdown("<h1 class='main-header'>Venture Scope Dashboard</h1>", unsafe_allow_html=True)
    
    # Sidebar styling
    st.sidebar.markdown("<div class='sidebar-header'>Business Configuration</div>", unsafe_allow_html=True)
    
    # Load data
    cities = load_cities()    
    industries = load_industries()
    
    # Sidebar inputs
    selected_industry = st.sidebar.selectbox("Select Business Domain", industries)
    selected_city = st.sidebar.multiselect("Ideal Business Location", sorted(cities))
    budget_range = st.sidebar.slider("Select Budget Range", 
                                     10000, 1000000, (100000, 500000), 
                                     format="$%d")
    
    # Initialize session state
    if "products" not in st.session_state:
        st.session_state.products = []
    if "api_results" not in st.session_state:
        st.session_state.api_results = None
    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    # Product input section
    st.sidebar.markdown("<div class='sidebar-header'>Product Configuration</div>", unsafe_allow_html=True)
    
    new_product = st.sidebar.text_input("Add a product:")
    if st.sidebar.button("Add Product", key="add_product", use_container_width=True):
        if new_product and new_product not in st.session_state.products:
            st.session_state.products.append(new_product)
            st.rerun()

    # Display added products with remove buttons
    if st.session_state.products:
        st.sidebar.markdown("**Your Products:**")
        for i, product in enumerate(st.session_state.products):
            cols = st.sidebar.columns([0.8, 0.2])
            cols[0].markdown(f"- {product}")
            if cols[1].button("❌", key=f"remove_{product}"):
                st.session_state.products.remove(product)
                st.rerun()
    
    # Business details
    st.sidebar.markdown("<div class='sidebar-header'>Business Details</div>", unsafe_allow_html=True)
    size = st.sidebar.selectbox("What is the size of business?", 
                               ["Startup", "Small Enterprise", "Medium Enterprise", "MNC"])
    additional_details = st.sidebar.text_area("What is your Unique Selling Proposition?")
    
    # Submit button with styling
    submit_button = st.sidebar.button("Submit Analysis Request", type="primary", use_container_width=True)
    
    if submit_button:
        if len(st.session_state.products) > 0 and selected_city:
            st.session_state.submitted = True
            
            # Create data payload
            data = {
                "industry": selected_industry,
                "product": st.session_state.products,
                "location/city": selected_city,
                "budget": list(budget_range),
                "size": size,
                "unique_selling_proposition": additional_details
            }
            
            # Create placeholder for loading message
            placeholder = st.empty()
            with placeholder.container():
                st.markdown("""
                <div class="success-box" style="text-align: center; padding: 20px;">
                    <h3>Your business proposal is being processed!</h3>
                    <p>This may take a few moments. Please wait while we analyze your data.</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Define the API calls to make
            api_calls = [
                ("location_intelligence", "location_intelligence", data)
            ]
            
            # Run the API calls asynchronously
            with st.spinner("🔍 Processing your business intelligence request..."):
                api_results = run_async_calls(api_calls)
                st.session_state.api_results = api_results
            
            placeholder.empty()
            
            # Display main content
            st.markdown(f"""
            <div class='info-box'>
                <h3>Analysis Results for {selected_industry}</h3>
                <p>Below are the results of your business intelligence analysis for {', '.join(selected_city)}.</p>
                <p><strong>Budget Range:</strong> ${budget_range[0]:,} to ${budget_range[1]:,}</p>
                <p><strong>Products:</strong> {', '.join(st.session_state.products)}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Displaying tabs for different sections
            market_analysis, trends, location_intelligence, regulations = st.tabs([
                "📊 Market Analysis", 
                "📈 Emerging Trends", 
                "🗺️ Location Intelligence", 
                "📝 State Regulations"
            ])    
            
            with market_analysis:
                st.markdown("<div class='subheader'>Industry Overview</div>", unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    <div class='metric-container' style='height:150px;'>
                        <div style='font-size:18px;'>Market Size</div>
                        <div class='metric-value' style='font-size:46px; margin-top:10px;'>$4.2T</div>
                        <div style='color:#4CAF50; margin-top:10px;'>+8.3% YoY Growth</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown("""
                    <div class='metric-container' style='height:150px;'>
                        <div style='font-size:18px;'>Growth Rate</div>
                        <div class='metric-value' style='font-size:46px; margin-top:10px;'>5.8%</div>
                        <div style='color:#4CAF50; margin-top:10px;'>Outpacing inflation by 2.3%</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("""
                <div class='card' style='margin-top:20px;'>
                    <h4>Industry Insights</h4>
                    <p>The healthcare industry includes providers, payers, and life sciences companies. It has shown remarkable resilience in recent years, with steady growth projected through 2030.</p>
                    <p>Key drivers include an aging population, technological advancements, and increased focus on preventative care.</p>
                </div>
                """, unsafe_allow_html=True)

            with trends:
                st.markdown("<div class='subheader'>Emerging Trends</div>", unsafe_allow_html=True)
                
                trends_data = [
                    {
                        "title": "Digital Transformation",
                        "description": "Financial institutions are rapidly adopting digital technologies to streamline operations and enhance customer experience.",
                        "impact": "High",
                        "icon": "💻"
                    },
                    {
                        "title": "Sustainable Finance",
                        "description": "Growing emphasis on ESG (Environmental, Social, and Governance) factors in investment decisions.",
                        "impact": "Medium",
                        "icon": "🌱"
                    },
                    {
                        "title": "Blockchain Integration",
                        "description": "Decentralized finance applications are being explored by traditional financial institutions.",
                        "impact": "Medium-High",
                        "icon": "🔗"
                    }
                ]
                
                for trend in trends_data:
                    st.markdown(f"""
                    <div class='card'>
                        <h3>{trend['icon']} {trend['title']}</h3>
                        <p><strong>Impact: </strong>{trend['impact']}</p>
                        <p>{trend['description']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.info("Financial services are experiencing rapid transformation with fintech adoption and digital banking leading the way.")

            with location_intelligence:
                st.markdown("<div class='subheader'>Location Intelligence</div>", unsafe_allow_html=True)
                
                location_data = st.session_state.api_results.get("location_intelligence", {})
                if "error" in location_data:
                    st.error(f"Error fetching location intelligence: {location_data['error']}")
                else:
                    display_locations(location_data.get("locations", []))
                    display_competitors(location_data.get("competitors", []))
            
            with regulations:
                st.markdown("<div class='subheader'>State Regulations</div>", unsafe_allow_html=True)
                
                st.markdown("""
                <div class='info-box'>
                    <h4>Regulatory Overview</h4>
                    <p>This section provides information about relevant regulations in your selected locations.</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.info("Note: Detailed regulatory analysis is currently in development. Please check back later for updates.")
                
                # Example regulatory info
                with st.expander("Business Licensing Requirements"):
                    st.markdown("""
                    <div class='card'>
                        <h4>General Business License</h4>
                        <p>Most businesses operating in New York City require a basic business license from the Department of Consumer Affairs.</p>
                        <p><strong>Estimated Cost:</strong> $100-$300 depending on business type</p>
                        <p><strong>Renewal:</strong> Every 2 years</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with st.expander("Food Service Regulations"):
                    st.markdown("""
                    <div class='card'>
                        <h4>Food Service Establishment Permit</h4>
                        <p>Required for businesses serving food and beverages.</p>
                        <p><strong>Estimated Cost:</strong> $280-$560</p>
                        <p><strong>Inspection:</strong> Required before opening</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Reset button
            if st.button("Start New Analysis", type="primary"):
                st.session_state.submitted = False
                st.session_state.api_results = None
                st.session_state.products = []
                st.rerun()
                
        else:
            if not st.session_state.products:
                st.error("Please add at least one product before submitting.")
            if not selected_city:
                st.error("Please select at least one location before submitting.")
    
    # Show welcome message when not submitted
    if not st.session_state.submitted:
        st.html("""
        <div class='info-box' style='padding: 2rem; text-align: center;'>
            <h2>Welcome to Venture Scope!</h2>
            <p style='font-size: 1.2rem; margin: 1rem 0;'>This tool helps you analyze potential business locations based on market intelligence data.</p>
            
            <div style='background-color: #f9f9f9; padding: 1.5rem; border-radius: 5px; margin: 1.5rem 0; text-align: left;'>
                <h3 style='margin-bottom: 1rem;'>How to use:</h3>
                <ol style='margin-left: 1.5rem;'>
                    <li>Select your business domain and target locations</li>
                    <li>Add your products or services</li>
                    <li>Set your budget range</li>
                    <li>Select your business size</li>
                    <li>Enter your unique selling proposition</li>
                    <li>Click Submit to start the analysis</li>
                </ol>
            </div>
            
            <p>The system will analyze market conditions, competition, and location suitability to provide recommendations for your business venture.</p>
        </div>
        """)
        
        # Demo images or examples
        st.markdown("<h3 style='margin-top: 2rem;'>Features</h3>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class='card' style='height: 200px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;'>
                <h3>🏙️ Location Analysis</h3>
                <p>Find the perfect location for your business based on multiple factors</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class='card' style='height: 200px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;'>
                <h3>🏢 Competitor Analysis</h3>
                <p>Understand your competition's strengths and weaknesses</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div class='card' style='height: 200px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;'>
                <h3>📊 Market Insights</h3>
                <p>Get valuable insights into market trends and opportunities</p>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()