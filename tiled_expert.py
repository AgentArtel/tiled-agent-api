from __future__ import annotations as _annotations

from dataclasses import dataclass
from dotenv import load_dotenv
import logfire
import asyncio
import httpx
import os

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI
from supabase import Client
from typing import List, Optional, Dict, Any

load_dotenv()

llm = os.getenv('LLM_MODEL', 'gpt-4')
model = OpenAIModel(llm)

logfire.configure(send_to_logfire='if-token-present')

@dataclass
class TiledAIDeps:
    supabase: Client
    openai_client: AsyncOpenAI

# Load system prompt from environment variable
system_prompt = os.getenv('SYSTEM_PROMPT', """
You are an expert at Tiled - a Python library for accessing scientific data. You have access to all the documentation.
Please help users understand and implement Tiled in their workflows.
""")

class TiledAIExpert:
    def __init__(self, supabase: Client, openai_client: AsyncOpenAI):
        self.supabase = supabase
        self.openai_client = openai_client

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector from OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return [0] * 1536  # Return zero vector on error

    async def get_relevant_docs(self, query: str) -> List[Dict[str, Any]]:
        """Get relevant documentation based on query."""
        try:
            # Get query embedding
            query_embedding = await self.get_embedding(query)
            print(f"Generated embedding of length: {len(query_embedding)}")

            # Search for similar docs
            print("Searching for similar docs...")
            response = self.supabase.rpc(
                'match_tiled_docs',
                {
                    'query_embedding': query_embedding,
                    'match_count': 5,
                    'filter': {'source': 'tiled_docs'}  # Filter by source
                }
            ).execute()
            
            print(f"Supabase response: {response}")
            if not response.data:
                print("No relevant documentation found")
                return []
                
            print(f"Found {len(response.data)} relevant documents")
            return response.data

        except Exception as e:
            print(f"Error getting relevant docs: {e}")
            print(f"Error type: {type(e)}")
            if hasattr(e, '__dict__'):
                print(f"Error attributes: {e.__dict__}")
            return []

    def format_sources(self, docs: List[Dict[str, Any]]) -> str:
        """Format source documents into a string."""
        print(f"Formatting sources from {len(docs)} documents")
        if not docs:
            return ""
        
        formatted_chunks = []
        for doc in docs:
            print(f"Processing doc: {doc}")
            if 'content' in doc and 'title' in doc:
                chunk_text = f"""
# {doc['title']}

{doc['content']}

Source: {doc.get('url', 'Unknown')}
Similarity: {doc.get('similarity', 0):.2f}
"""
                formatted_chunks.append(chunk_text)
        
        formatted = "\n\n---\n\n".join(formatted_chunks)
        print(f"Formatted sources: {formatted}")
        return formatted

    async def generate_response(self, docs: List[Dict[str, Any]], query: str) -> str:
        """Generate response using OpenAI."""
        try:
            # Prepare context from docs
            context_parts = []
            for doc in docs:
                if 'content' in doc:
                    context_parts.append(f"# {doc.get('title', 'Documentation')}\n\n{doc['content']}")
            
            context = "\n\n---\n\n".join(context_parts) if context_parts else ""
            
            # Prepare messages
            messages = [
                {
                    "role": "system", 
                    "content": """You are an expert in Tiled Map Editor, a general purpose map editor. 
                    You help users understand how to use Tiled to create and edit maps for their games and applications.
                    Always be specific and provide step-by-step instructions when explaining how to do something.
                    If you're not sure about something, say so rather than making assumptions."""
                },
                {"role": "user", "content": f"Context from Tiled documentation:\n\n{context}\n\nQuestion: {query}"}
            ]
            
            # Get response from OpenAI
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating response: {e}")
            return f"Error generating response: {str(e)}"

tiled_expert = Agent(
    model,
    system_prompt=system_prompt,
    deps_type=TiledAIDeps,
    retries=2
)

@tiled_expert.tool
async def retrieve_relevant_documentation(ctx: RunContext[TiledAIDeps], user_query: str) -> str:
    """
    Retrieve relevant documentation chunks based on the query with RAG.
    
    Args:
        ctx: The context including the Supabase client and OpenAI client
        user_query: The user's question or query
        
    Returns:
        A formatted string containing the top 5 most relevant documentation chunks
    """
    expert = TiledAIExpert(ctx.deps.supabase, ctx.deps.openai_client)
    docs = await expert.get_relevant_docs(user_query)
    return expert.format_sources(docs)

@tiled_expert.tool
async def list_documentation_pages(ctx: RunContext[TiledAIDeps]) -> List[str]:
    """
    Retrieve a list of all available Tiled documentation pages.
    
    Returns:
        List[str]: List of unique URLs for all documentation pages
    """
    try:
        result = ctx.deps.supabase.table('tiled_docs').select('url').execute()
        if result.data:
            # Get unique URLs
            urls = {doc['url'] for doc in result.data}
            return sorted(list(urls))
        return []
    except Exception as e:
        print(f"Error listing documentation pages: {e}")
        return []

@tiled_expert.tool
async def get_page_content(ctx: RunContext[TiledAIDeps], url: str) -> str:
    """
    Retrieve the full content of a specific documentation page by combining all its chunks.
    
    Args:
        ctx: The context including the Supabase client
        url: The URL of the page to retrieve
        
    Returns:
        str: The complete page content with all chunks combined in order
    """
    try:
        result = ctx.deps.supabase.table('tiled_docs')\
            .select('chunk_number,content')\
            .eq('url', url)\
            .order('chunk_number')\
            .execute()
            
        if not result.data:
            return f"No content found for URL: {url}"
            
        # Combine chunks in order
        chunks = sorted(result.data, key=lambda x: x['chunk_number'])
        return "\n\n".join(chunk['content'] for chunk in chunks)
        
    except Exception as e:
        return f"Error retrieving page content: {e}"