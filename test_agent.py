import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_tiled_agent():
    # API endpoint
    url = "http://localhost:8000/api/ask"
    
    # Headers with bearer token
    headers = {
        "Authorization": f"Bearer {os.getenv('API_BEARER_TOKEN')}",
        "Content-Type": "application/json"
    }
    
    # Test query that requires knowledge from multiple sources
    data = {
        "query": """How can I create a multi-layered RPG map with the following requirements:
        1. A ground layer with animated water tiles
        2. An object layer for NPCs with custom properties for dialog
        3. A collision layer for defining walkable areas
        Please provide specific Python code examples using the Tiled library.""",
        "user_id": "test_user",
        "session_id": "test_session",
        "context": "Creating an RPG game map",
        "collaborative": False
    }
    
    # Send request
    response = requests.post(url, json=data, headers=headers)
    
    # Print results
    if response.status_code == 200:
        result = response.json()
        print("\nAgent Response:")
        print(result["response"])
        print("\nSource Documents:")
        for doc in result["source_documents"]:
            print(f"\n- {doc.get('url', 'No URL')}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_tiled_agent()
