from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
import os

from tiled_expert import TiledAIExpert

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Tiled Documentation Agent API",
             description="API for querying Tiled Map Editor documentation")
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
    os.getenv("SUPABASE_URL", ""),
    os.getenv("SUPABASE_SERVICE_KEY", "")
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
            detail="API token not configured on server"
        )
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid API token"
        )
    return True

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "Tiled Documentation Agent API",
        "version": "1.0.0",
        "description": "API for querying Tiled Map Editor documentation"
    }

@app.post("/api/ask", response_model=AgentResponse)
async def tiled_expert_endpoint(
    request: AgentRequest,
    authenticated: bool = Depends(verify_token)
) -> AgentResponse:
    """
    Main endpoint for querying the Tiled documentation.
    Requires bearer token authentication.
    """
    try:
        # Initialize the AI expert
        ai_expert = TiledAIExpert(
            supabase=supabase,
            openai_client=openai_client
        )

        # Generate response
        response = await ai_expert.generate_response([], request.query)
        docs = await ai_expert.get_relevant_docs(request.query)
        sources = ai_expert.format_sources(docs)

        return AgentResponse(
            response=response,
            source_documents=sources.split("\n") if sources else []
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
