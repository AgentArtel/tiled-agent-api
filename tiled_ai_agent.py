from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
import os
import json
from agent_communication import AgentCommunication

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
agent_communication = AgentCommunication()

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

async def get_relevant_context(query: str) -> List[Dict[str, Any]]:
    """Get relevant documentation context from Supabase."""
    # Get embeddings for the query
    response = await openai_client.embeddings.create(
        input=query,
        model="text-embedding-ada-002"
    )
    query_embedding = response.data[0].embedding

    # Search for similar documents in Supabase
    response = supabase.rpc(
        'match_tiled_docs',
        json.dumps({
            'query_embedding': query_embedding,
            'match_count': 5,
            'match_threshold': 0.78
        })
    ).execute()

    return response.data if response.data else []

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
        # Get relevant documentation context
        docs = await get_relevant_context(request.query)
        context = "\n\n".join([doc['content'] for doc in docs])

        # Include context in the query if provided
        system_prompt = os.getenv("SYSTEM_PROMPT", """You are an expert at Tiled - a Python library for accessing scientific data. 
        Your task is to help users understand how to use Tiled effectively.
        Always provide clear, accurate, and helpful responses with code examples when relevant.""")

        # Create chat completion
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context from Tiled documentation:\n\n{context}\n\nQuestion: {request.query}"}
        ]

        response = await openai_client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4"),
            messages=messages
        )

        # If collaborative mode is enabled, get insights from other agents
        collaborative_insights = None
        if request.collaborative:
            collaborative_insights = await agent_communication.collaborative_map_design(request.query)

        return AgentResponse(
            response=response.choices[0].message.content,
            source_documents=[{
                'url': doc['url'],
                'title': doc['title'],
                'content': doc['content'][:200] + "..."  # Truncate content for response
            } for doc in docs],
            collaborative_insights=collaborative_insights
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
