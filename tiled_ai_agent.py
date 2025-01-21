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
    collaborative: bool = False

class AgentResponse(BaseModel):
    response: str
    source_documents: List[Dict[str, Any]] = []
    collaborative_insights: Optional[Dict[str, Any]] = None

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

@app.post("/api/ask")
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
            system_prompt="""You are an expert at Tiled Map Editor and its Python library.
Your role is to help developers understand and use Tiled effectively for creating game maps.

When responding to questions:
1. Be concise and direct
2. Provide code examples when relevant
3. Reference official documentation
4. Explain concepts in a way that's easy for developers to understand
5. If you're not sure about something, say so rather than making assumptions

Remember to:
- Focus on practical, working solutions
- Highlight best practices for map creation
- Consider performance implications
- Mention any relevant plugins or extensions
- Point out common pitfalls to avoid"""
        )
        
        # Include context in the query if provided
        full_query = f"{request.context}\n\nQuestion: {request.query}" if request.context else request.query
        
        # Run the agent
        result = await agent.run(full_query)
        
        return AgentResponse(
            response=result.data,
            source_documents=[],  # TODO: Add relevant source documents
            collaborative_insights=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
