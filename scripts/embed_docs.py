import os
import asyncio
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import httpx
from openai import AsyncOpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

async def fetch_documentation(base_url: str = "https://tiled.readthedocs.io/en/latest/") -> List[Dict[str, str]]:
    """Fetch documentation pages from Tiled's ReadTheDocs."""
    async with httpx.AsyncClient() as client:
        # Get the main page
        response = await client.get(base_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        docs = []
        # Find all documentation links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http'):
                url = href
            else:
                url = base_url.rstrip('/') + '/' + href.lstrip('/')
            
            try:
                page_response = await client.get(url)
                page_soup = BeautifulSoup(page_response.text, 'html.parser')
                
                # Get main content
                content = page_soup.find('div', {'role': 'main'})
                if content:
                    text = content.get_text(separator='\n', strip=True)
                    # Split into smaller chunks
                    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
                    for chunk in chunks:
                        docs.append({
                            'content': chunk,
                            'url': url
                        })
            except Exception as e:
                print(f"Error fetching {url}: {str(e)}")
                continue
                
        return docs

async def get_embedding(text: str) -> List[float]:
    """Get embedding for text using OpenAI's API."""
    response = await openai_client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding

async def store_documents(docs: List[Dict[str, str]]):
    """Store documents and their embeddings in Supabase."""
    for doc in docs:
        try:
            embedding = await get_embedding(doc['content'])
            
            # Store in Supabase
            supabase.table('documentation').insert({
                'content': doc['content'],
                'url': doc['url'],
                'embedding': embedding
            }).execute()
            
            print(f"Stored document from {doc['url']}")
        except Exception as e:
            print(f"Error storing document: {str(e)}")
            continue

async def main():
    """Main function to fetch and store documentation."""
    print("Fetching documentation...")
    docs = await fetch_documentation()
    print(f"Found {len(docs)} documentation chunks")
    
    print("Storing documents with embeddings...")
    await store_documents(docs)
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
