import streamlit as st
import pandas as pd

@st.cache_data
def load_cities():
    df = pd.read_csv("frontend/uscities.csv")
    df['city_state'] = df['city'] + ", " + df['state_name']
    return df['city_state'].dropna().unique()


def main():
    st.title("Venture Scope")
    st.sidebar.header("Main Menu")
    cities = load_cities()    
    industries = ["Consumer Products & Services", "Financial Services", "Information Technology", "Retail", "Material & Resources", "Others"]
    selected_industry = st.sidebar.selectbox("Select Business Domain", industries)
    selected_city = st.sidebar.multiselect("Ideal Business Location", sorted(cities))
    budget_range = st.sidebar.slider("Select Budget Range", 10000, 1000000, (100000, 500000))
    product = st.sidebar.text_input("What is going to be your product?")
    size = st.sidebar.selectbox("What is the size of business?", ["Startup", "SME", "MNC"])
    additional_details = st.sidebar.text_area("Any notes you might want to add?")
    if st.sidebar.button("Submit"):
        st.write("Processing your request...")
        st.write(f"You selected: **{selected_industry}**")
        st.write(f"You selected: **{selected_city}**")
        st.write(f"You selected: **{budget_range}**")
        st.write(f"You selected: **{product}**")
        st.write(f"You selected: **{size}**")
        st.write(f"You selected: **{additional_details}**")
        # Here you would call the backend API with the selected options
        # For now, we will just display a success message
        st.success("Your business proposal is being processed. Please check back later.")
    
if __name__ == "__main__":
# Set page configuration
    st.set_page_config(
        page_title="Venture Scope",
        layout="wide",
        initial_sidebar_state="expanded"
    )    
    main()