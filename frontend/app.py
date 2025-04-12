import streamlit as st
import pandas as pd
import time

@st.cache_data
def load_cities():
    df = pd.read_csv("frontend/uscities.csv")
    df['city_state'] = df['city'] + ", " + df['state_name']
    return df['city_state'].dropna().unique()

@st.cache_data
def load_industries():
    industries = [
        "Consumer Products & Services",
        "Financial Services",
        "Information Technology",
        "Retail",
        "Material & Resources",
        "Others"
        ]
    return industries

def main():
    st.title("Venture Scope Dashboard")
    st.sidebar.header("Main Menu")
    
    # Load data
    cities = load_cities()    
    industries = load_industries()
    
    # Sidebar inputs
    selected_industry = st.sidebar.selectbox("Select Business Domain", industries)
    selected_city = st.sidebar.multiselect("Ideal Business Location", sorted(cities))
    budget_range = st.sidebar.slider("Select Budget Range", 10000, 1000000, (100000, 500000))
    
    # Initialize session state for products
    if "products" not in st.session_state:
        st.session_state.products = []

    # Product input
    new_product = st.sidebar.text_input("Add a product:")
    if st.sidebar.button("Add Product"):
        if new_product and new_product not in st.session_state.products:
            st.session_state.products.append(new_product)
            # st.sidebar.success(f"Added: {new_product}")
            st.rerun()  # Immediate update

    # Display added products with remove buttons
    product_to_remove = None
    if st.session_state.products:
        st.sidebar.markdown("**Your Products:**")
        for i, product in enumerate(st.session_state.products):
            cols = st.sidebar.columns([0.8, 0.2])
            cols[0].markdown(f"- {product}")
            if cols[1].button("❌", key=f"remove_{product}"):
                product_to_remove = product

    # Actually remove product and rerun
    if product_to_remove:
        st.session_state.products.remove(product_to_remove)
        st.rerun()
    
    size = st.sidebar.selectbox("What is the size of business?", ["Startup", "Small Enterprise", "Medium Enterprise", "MNC"])
    additional_details = st.sidebar.text_area("What is your Unique Selling Proposition?")
    
    if st.sidebar.button("Submit"):
        if st.session_state.products is None:
            # Here you would call the backend API with the selected options
            # For now, we will just display a success message
            placeholder = st.empty()  # Create an empty placeholder
            with placeholder:
                st.success("Your business proposal is being processed. Please check back later.")
            st.write(f"Selected Industry: {selected_industry}")
            st.write(f"Selected City: {', '.join(selected_city)}")
            st.write(f"Budget Range: ${budget_range[0]} to ${budget_range[1]}")
            st.write(f"Selected Products: {', '.join(st.session_state.products)}")
            st.write(f"Business Size: {size}")
            st.write(f"Additional Details: {additional_details}")
            
            # Displaying tabs for different sections
            market_anlysis, trends, location_intelligence, regulations = st.tabs(["Market Analysis", "Emerging Trends", "Location Intelligence", "State Regulations Chat"])    
            with market_anlysis:
                st.subheader(f"{selected_industry} Overview")
                col1, col2 = st.columns(2)
                col1.metric("Market Size", "$4.2T")
                col2.metric("Growth Rate", "5.8%")
                st.write("The healthcare industry includes providers, payers, and life sciences.")

            with trends:
                st.subheader("Finance Overview")
                st.info("Includes banking, insurance, and capital markets.")
                st.write("Fintech adoption and digital banking are rapidly transforming this sector.")

            with location_intelligence:
                st.subheader("Technology Overview")
                st.success("Booming due to AI, cloud, and edge computing.")
                st.write("Covers software, hardware, and IT services across various verticals.")
                
            time.sleep(3)
            placeholder.empty()  # Remove the placeholder after processing
            st.session_state.products.clear()  # Clear the products list after submission
        else:
            st.error("Please add at least one product before submitting.")
            
if __name__ == "__main__":
    # Set page configuration
    st.set_page_config(
        page_title="Venture Scope",
        layout="wide",
        initial_sidebar_state="expanded"
    )    
    main()