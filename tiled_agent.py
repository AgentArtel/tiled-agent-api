from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
import os

from pydantic_ai import Agent

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Tiled Documentation Agent API",
             description="API for querying Tiled documentation")
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

class AgentRequest(BaseModel):
    query: str
    user_id: str = "default"
    session_id: str = "default"
    context: str = ""

class AgentResponse(BaseModel):
    response: str
    source_documents: List[str] = []

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """Verify the bearer token against environment variable."""
    expected_token = os.getenv("API_BEARER_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=500,
            detail="API_BEARER_TOKEN environment variable not set"
        )
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    return True

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "Tiled Documentation Agent API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.post("/ask")
async def tiled_expert_endpoint(
    request: AgentRequest,
    authenticated: bool = Depends(verify_token)
):
    """
    Main endpoint for querying the Tiled documentation.
    Requires bearer token authentication.
    """
    try:
        # Initialize the agent with OpenAI model
        agent = Agent(
            model="openai:gpt-4",
            system_prompt="""You are an expert at Tiled - a Python library for accessing scientific data. You have access to all the Tiled documentation, including examples, API reference, and other resources to help users work with Tiled.

Your job is to assist users with:
1. Understanding Tiled's core concepts and architecture
2. Implementing Tiled in their data workflows
3. Troubleshooting Tiled-related issues
4. Best practices for scientific data access with Tiled

Always make sure to look at the documentation before answering questions unless you're completely certain of the answer. Start with the most relevant documentation using RAG, then check specific pages if needed.

Be direct and proactive - don't ask before taking actions like searching documentation. If you don't find an answer in the docs, be honest about it.

Focus on practical, implementation-focused answers that help users solve their data access and management challenges with Tiled."""
        )
        
        # Include context in the query if provided
        full_query = f"{request.context}\n\nQuestion: {request.query}" if request.context else request.query
        
        # Run the agent
        result = await agent.run(full_query)
        
        return AgentResponse(
            response=result.data,
            source_documents=[]  # We can add relevant source documents later
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
