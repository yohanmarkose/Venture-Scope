import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys
import json
import pandas as pd


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(project_root)

from fastapi.testclient import TestClient

# Mock external dependencies before importing modules that use them
mock_openai = MagicMock()
mock_s3_file_manager = MagicMock()
mock_snowflake = MagicMock()
mock_location_intelligence = AsyncMock()
mock_run_agents = MagicMock()
mock_run_chatbot = MagicMock()
mock_chat_with_expert = MagicMock()

# Apply patches
patches = [
    patch('backend.app.main.openai.OpenAI', return_value=mock_openai),
    patch('backend.app.main.S3FileManager', return_value=mock_s3_file_manager),
    patch('backend.app.main.SnowflakeConnector', return_value=mock_snowflake),
    patch('features.mcp.google_maps.location_intelligence.start_location_intelligence', return_value=mock_location_intelligence),
    patch('features.market_analysis.run_agents', return_value=mock_run_agents),
    patch('features.qa_agent.run_chatbot', return_value=mock_run_chatbot),
    patch('features.chat_with_expert.chat_with_expert_endpoint', return_value=mock_chat_with_expert)
]

for p in patches:
    p.start()

# Now import the modules that depend on these
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from backend.app.main import app, convert_report_to_markdown, get_graph

# --- FastAPI Tests ---
client = TestClient(app)

# --- Basic API Tests ---

def test_root_endpoint():
    """Test the root endpoint returns the welcome message"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == "Welcome to the Venture-Scope API!"
    
def test_health_check():
    """Test the health check endpoint returns OK status"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# --- Market Analysis Tests ---

def test_market_analysis_missing_fields():
    """Test market analysis endpoint with missing required fields"""
    # Test incomplete data
    test_data = {
        "industry": "Food and Beverage",
        "product": ["Coffee", "Tea", "Pastries"],
        # Missing location/city
        "budget": [120000, 300000],
        "size": "Small Enterprise"
    }
    
    # Make request
    response = client.post("/market_analysis", json=test_data)
    
    # Assertions
    assert response.status_code == 422  # Unprocessable Entity for validation errors

def test_market_analysis_invalid_data():
    """Test market analysis endpoint with invalid data types"""
    # Test invalid data types
    test_data = {
        "industry": "Food and Beverage",
        "product": ["Coffee", "Tea", "Pastries"],
        "location/city": ["Manhattan, New York"],
        "budget": "invalid_budget",  # Should be an array of numbers
        "size": "Small Enterprise"
    }
    
    # Make request
    response = client.post("/market_analysis", json=test_data)
    
    # Assertions
    assert response.status_code == 422  # Unprocessable Entity for validation errors

def test_market_analysis_industry_classification_error():
    """Test market analysis endpoint when industry classification fails"""
    # Setup mock responses to simulate classification error
    with patch('backend.app.main.classify_industry', return_value=None):
        test_data = {
            "industry": "Invalid Industry",
            "product": ["Invalid Product"],
            "location/city": ["Invalid Location"],
            "budget": [0, 0],
            "size": "Invalid Size",
            "unique_selling_proposition": "Invalid USP"
        }
        
        # Make request
        response = client.post("/market_analysis", json=test_data)
        
        # Assertions
        assert response.status_code == 500
        assert "Error answering question" in response.json()["detail"]

def test_market_analysis_graph_error():
    """Test market analysis endpoint when graph generation fails"""
    # Setup mock responses for initial success
    mock_openai.chat.completions.create.return_value.choices[0].message.content = "food & beverages"
    
    # Make get_graph raise an exception
    with patch('backend.app.main.get_graph', side_effect=Exception("Graph error")):
        test_data = {
            "industry": "Food and Beverage",
            "product": ["Coffee", "Tea", "Pastries"],
            "location/city": ["Manhattan, New York"],
            "budget": [120000, 300000],
            "size": "Small Enterprise",
            "unique_selling_proposition": "High Quality, Organic, Locally Sourced Ingredients"
        }
        
        # Make request
        response = client.post("/market_analysis", json=test_data)
        
        # Assertions
        assert response.status_code == 500
        assert "Error answering question" in response.json()["detail"]

def test_market_analysis_agent_error():
    """Test market analysis endpoint when agent fails"""
    # Setup mock responses for initial success
    mock_openai.chat.completions.create.return_value.choices[0].message.content = "food & beverages"
    
    fig_mock = MagicMock()
    fig_mock.to_json.return_value = '{"data":[{"type":"choropleth"}],"layout":{}}'
    
    # Mock get_graph function
    with patch('backend.app.main.get_graph', return_value=fig_mock):
        # Make run_agents raise an exception
        with patch('features.market_analysis.run_agents', side_effect=Exception("Agent error")):
            test_data = {
                "industry": "Food and Beverage",
                "product": ["Coffee", "Tea", "Pastries"],
                "location/city": ["Manhattan, New York"],
                "budget": [120000, 300000],
                "size": "Small Enterprise",
                "unique_selling_proposition": "High Quality, Organic, Locally Sourced Ingredients"
            }
            
            # Make request
            response = client.post("/market_analysis", json=test_data)
            
            # Assertions
            assert response.status_code == 500
            assert "Error answering question" in response.json()["detail"]

# --- Location Intelligence Tests ---

def test_location_intelligence_missing_fields():
    """Test location intelligence endpoint with missing required fields"""
    # Test incomplete data
    test_data = {
        "industry": "Food and Beverage",
        "product": ["Coffee", "Tea", "Pastries"],
        # Missing location/city
        "budget": [120000, 300000],
        "size": "Small Enterprise"
    }
    
    # Make request
    response = client.post("/location_intelligence", json=test_data)
    
    # Assertions
    assert response.status_code == 422  # Unprocessable Entity for validation errors

def test_location_intelligence_invalid_data():
    """Test location intelligence endpoint with invalid data types"""
    # Test invalid data types
    test_data = {
        "industry": "Food and Beverage",
        "product": ["Coffee", "Tea", "Pastries"],
        "location/city": ["Manhattan, New York"],
        "budget": "invalid_budget",  # Should be an array of numbers
        "size": "Small Enterprise"
    }
    
    # Make request
    response = client.post("/location_intelligence", json=test_data)
    
    # Assertions
    assert response.status_code == 422  # Unprocessable Entity for validation errors

# --- Helper Function Tests ---

def test_convert_report_to_markdown_dict():
    """Test report conversion with dictionary input"""
    # Test with dictionary input
    report_dict = {
        "market_players": "Test players",
        "competitor_details": "Test competitors",
        "industry_overview": "Test overview",
        "industry_trends": "Test trends",
        "sources": "Test sources"
    }
    
    result = convert_report_to_markdown(report_dict)
    
    # Assertions
    assert "## Industry Overview" in result
    assert "Test overview" in result
    assert "## Market Players" in result
    assert "Test players" in result
    assert "## Competitor Details" in result
    assert "Test competitors" in result
    assert "## Industry Trends" in result
    assert "Test trends" in result
    assert "## Sources" in result
    assert "Test sources" in result

def test_convert_report_to_markdown_json():
    """Test report conversion with JSON string input"""
    # Test with JSON string input
    report_dict = {
        "market_players": "Test players",
        "competitor_details": "Test competitors",
        "industry_overview": "Test overview",
        "industry_trends": "Test trends",
        "sources": "Test sources"
    }
    json_input = json.dumps(report_dict)
    
    result = convert_report_to_markdown(json_input)
    
    # Assertions
    assert "## Industry Overview" in result
    assert "Test overview" in result
    assert "## Market Players" in result
    assert "Test players" in result
    assert "## Competitor Details" in result
    assert "Test competitors" in result
    assert "## Industry Trends" in result
    assert "Test trends" in result
    assert "## Sources" in result
    assert "Test sources" in result

def test_convert_report_to_markdown_missing_fields():
    """Test report conversion with missing fields"""
    # Test with missing fields
    report_dict = {
        "market_players": "Test players",
        # Missing competitor_details
        "industry_overview": "Test overview",
        # Missing industry_trends
        # Missing sources
    }
    
    result = convert_report_to_markdown(report_dict)
    
    # Assertions
    assert "## Industry Overview" in result
    assert "Test overview" in result
    assert "## Market Players" in result
    assert "Test players" in result
    assert "## Competitor Details" in result
    assert "Competitor details not available" in result
    assert "## Industry Trends" in result
    assert "Industry trends not available" in result
    assert "## Sources" in result
    assert "Sources not provided" in result

def test_convert_report_to_markdown_invalid_json():
    """Test report conversion with invalid JSON string"""
    # Test with invalid JSON
    invalid_json = "This is not valid JSON"
    
    result = convert_report_to_markdown(invalid_json)
    
    # Assertions
    assert result == invalid_json  # Should return input as is

@patch('backend.app.main.SnowflakeConnector')
def test_get_graph_unknown_states(mock_snowflake_class):
    """Test graph generation with unknown states"""
    # Setup mock responses with unknown state
    mock_sf = MagicMock()
    mock_sf.get_statewise_count_by_industry.return_value = pd.DataFrame({
        'REGION': ['California', 'Unknown_State', 'Texas'],
        'COUNT': [100, 75, 50]
    })
    mock_snowflake_class.return_value = mock_sf
    
    # Call the function
    with patch('backend.app.main.warnings.warn') as mock_warn:
        result = get_graph("food & beverages")
    
    # Assertions
    assert result is not None
    mock_warn.assert_called_once()  # Warning should be issued for unknown state

@patch('backend.app.main.SnowflakeConnector')
def test_get_graph_connection_error(mock_snowflake_class):
    """Test graph generation when Snowflake connection fails"""
    # Setup mock to raise an exception on connect
    mock_sf = MagicMock()
    mock_sf.connect.side_effect = Exception("Connection error")
    mock_snowflake_class.return_value = mock_sf
    
    # Call the function - should raise the exception
    with pytest.raises(Exception):
        get_graph("food & beverages")