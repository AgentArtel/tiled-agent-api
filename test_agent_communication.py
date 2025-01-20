"""Test script for agent communication."""
import asyncio
import sys
from agent_communication import AgentCommunication

async def test_agent_communication(custom_query: str = None):
    """Test the agent communication system."""
    agent_comm = AgentCommunication()
    
    # Print configuration
    print("🔧 Configuration:")
    print(f"RPGJS API URL: {agent_comm.rpgjs_api_url}")
    print(f"Pydantic API URL: {agent_comm.pydantic_api_url}")
    print(f"Auth Token (first 10 chars): {agent_comm.api_bearer_token[:10]}...")
    print(f"Headers: {agent_comm.headers}")
    
    # Use custom query if provided, otherwise use default test case
    test_request = custom_query if custom_query else """
    I'm creating a map for an AI-controlled merchant NPC that roams between 
    different market areas. The NPC's behavior should change based on the 
    time of day and the area they're in.
    """
    
    print("\n🔄 Testing agent communication...")
    print("\n📝 Test request:", test_request)
    
    try:
        # Test RPGJS agent
        print("\n🎮 Testing RPGJS agent connection...")
        rpgjs_response = await agent_comm.ask_rpgjs_agent(
            test_request,
            {"query_type": "implementation"}
        )
        print("✅ RPGJS Response:", rpgjs_response)
        
        # Test Pydantic agent
        print("\n🔍 Testing Pydantic agent connection...")
        pydantic_response = await agent_comm.ask_pydantic_agent(
            test_request,
            {"query_type": "schema"}
        )
        print("✅ Pydantic Response:", pydantic_response)
        
        # Test full collaborative design
        print("\n🤝 Testing collaborative map design...")
        design_response = await agent_comm.collaborative_map_design(test_request)
        print("\n✅ Collaborative Design Response:")
        print("- Analysis:", design_response["analysis"])
        print("- Map Recommendations:")
        print("  - Layers:", design_response["map_recommendations"]["layers"])
        print("  - Properties:", design_response["map_recommendations"]["properties"])
        print("  - Events:", design_response["map_recommendations"]["events"])
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    # Get custom query from command line arguments if provided
    custom_query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    asyncio.run(test_agent_communication(custom_query))
