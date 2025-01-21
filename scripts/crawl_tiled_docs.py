import os
import sys
import json
import asyncio
import requests
from xml.etree import ElementTree
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from bs4 import BeautifulSoup

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from openai import AsyncOpenAI
from supabase import create_client, Client

load_dotenv()

# Initialize OpenAI and Supabase clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

@dataclass
class ProcessedChunk:
    url: str
    chunk_number: int
    title: str
    summary: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float]

def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    """Split text into chunks, respecting code blocks and paragraphs."""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position
        end = start + chunk_size

        # If we're at the end of the text, just take what's left
        if end >= text_length:
            chunks.append(text[start:].strip())
            break

        # Try to find a code block boundary first (```)
        chunk = text[start:end]
        code_block = chunk.rfind('```')
        if code_block != -1 and code_block > chunk_size * 0.3:
            end = start + code_block

        # If no code block, try to break at a paragraph
        elif '\n\n' in chunk:
            # Find the last paragraph break
            last_break = chunk.rfind('\n\n')
            if last_break > chunk_size * 0.3:  # Only break if we're past 30% of chunk_size
                end = start + last_break

        # If no paragraph break, try to break at a sentence
        elif '. ' in chunk:
            # Find the last sentence break
            last_period = chunk.rfind('. ')
            if last_period > chunk_size * 0.3:  # Only break if we're past 30% of chunk_size
                end = start + last_period + 1

        # Extract chunk and clean it up
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position for next chunk
        start = max(start + 1, end)

    return chunks

async def get_title_and_summary(chunk: str, url: str) -> Dict[str, str]:
    """Extract title and summary using GPT-4."""
    system_prompt = """You are an AI that extracts titles and summaries from documentation chunks.
    Return a JSON object with 'title' and 'summary' keys.
    For the title: If this seems like the start of a document, extract its title. If it's a middle chunk, derive a descriptive title.
    For the summary: Create a concise summary of the main points in this chunk.
    Keep both title and summary concise but informative."""
    
    try:
        response = await openai_client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"URL: {url}\n\nContent:\n{chunk[:1000]}..."}  # Send first 1000 chars for context
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error getting title and summary: {e}")
        return {"title": "Error processing title", "summary": "Error processing summary"}

async def get_embedding(text: str) -> List[float]:
    """Get embedding vector from OpenAI."""
    try:
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 1536  # Return zero vector on error

async def process_chunk(chunk: str, chunk_number: int, url: str) -> ProcessedChunk:
    """Process a single chunk of text."""
    # Get title and summary
    extracted = await get_title_and_summary(chunk, url)
    
    # Get embedding
    embedding = await get_embedding(chunk)
    
    # Create metadata
    metadata = {
        "source": "tiled_docs",
        "chunk_size": len(chunk),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "url_path": urlparse(url).path
    }
    
    return ProcessedChunk(
        url=url,
        chunk_number=chunk_number,
        title=extracted['title'],
        summary=extracted['summary'],
        content=chunk,  # Store the original chunk content
        metadata=metadata,
        embedding=embedding
    )

async def insert_chunk(chunk: ProcessedChunk):
    """Insert a processed chunk into Supabase."""
    try:
        data = {
            "url": chunk.url,
            "chunk_number": chunk.chunk_number,
            "title": chunk.title,
            "summary": chunk.summary,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding
        }
        
        result = supabase.table("tiled_docs").insert(data).execute()
        print(f"Inserted chunk {chunk.chunk_number} for {chunk.url}")
        return result
    except Exception as e:
        print(f"Error inserting chunk: {e}")
        return None

async def process_and_store_document(url: str, markdown: str):
    """Process a document and store its chunks in parallel."""
    # Split into chunks
    chunks = chunk_text(markdown)
    
    # Process chunks in parallel
    tasks = [
        process_chunk(chunk, i, url) 
        for i, chunk in enumerate(chunks)
    ]
    processed_chunks = await asyncio.gather(*tasks)
    
    # Store chunks in parallel
    insert_tasks = [
        insert_chunk(chunk) 
        for chunk in processed_chunks
    ]
    await asyncio.gather(*insert_tasks)

async def crawl_parallel(urls: List[str], max_concurrent: int = 5):
    """Crawl multiple URLs in parallel with a concurrency limit."""
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    # Create the crawler instance
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_url(url: str):
            async with semaphore:
                result = await crawler.arun(
                    url=url,
                    config=crawl_config,
                    session_id="session1"
                )
                if result.success:
                    print(f"Successfully crawled: {url}")
                    await process_and_store_document(url, result.markdown_v2.raw_markdown)
                else:
                    print(f"Failed: {url} - Error: {result.error_message}")
        
        # Process all URLs in parallel with limited concurrency
        await asyncio.gather(*[process_url(url) for url in urls])
    finally:
        await crawler.close()

async def get_tiled_docs_urls() -> List[str]:
    """Get URLs focused on comprehensive API understanding and advanced Tiled features for agent-to-agent communication."""
    urls = set()
    
    # Tiled Map Editor documentation
    map_editor_base = "https://doc.mapeditor.org/en/stable/"
    map_editor_urls = [
        # Core Concepts & Architecture
        "manual/introduction",
        "manual/getting-started",
        
        # Advanced Map Structure
        "manual/layers",
        "manual/layers/#layer-types",  # Comprehensive layer system understanding
        "manual/layers/#parallax-scrolling-factor",  # Advanced visual effects
        "manual/layers/#opacity-and-visibility",  # Layer manipulation
        "manual/layers/#offsets-and-scaling",  # Advanced layer transformations
        "manual/layers/#tinting-layers",  # Advanced visual customization
        
        # Advanced Tile Management
        "manual/editing-tile-layers",
        "manual/editing-tile-layers/#stamp-brush",
        "manual/editing-tile-layers/#terrain-brush",  # Advanced terrain handling
        "manual/editing-tile-layers/#bucket-fill-tool",
        "manual/editing-tile-layers/#selection-tools",  # Advanced selection techniques
        
        # Game Object System
        "manual/objects",
        "manual/objects/#placement-tools",
        "manual/objects/#object-types",  # Type system for game entities
        "manual/objects/#object-properties",  # Advanced object configuration
        "manual/objects/#edit-polygons",  # Complex collision shapes
        "manual/objects/#connecting-objects",  # Object relationships
        
        # Advanced Tileset Features
        "manual/editing-tilesets",
        "manual/editing-tilesets/#tileset-properties",
        "manual/editing-tilesets/#tile-properties",
        "manual/editing-tilesets/#tile-collision-editor",
        "manual/editing-tilesets/#tile-animation-editor",
        "manual/editing-tilesets/#wang-sets",  # Advanced tile transitions
        "manual/editing-tilesets/#terrain-information",  # Terrain system
        
        # Property System Architecture
        "manual/custom-properties",
        "manual/custom-properties/#adding-properties",
        "manual/custom-properties/#custom-types",  # Type system
        "manual/custom-properties/#presets",  # Reusable configurations
        "manual/custom-properties/#tile-property-inheritance",  # Advanced property system
        
        # Template System
        "manual/using-templates",
        "manual/using-templates/#creating-templates",
        "manual/using-templates/#creating-template-instances",
        "manual/using-templates/#editing-templates",  # Template management
        "manual/using-templates/#detaching-template-instances",  # Advanced template usage
        
        # Advanced World Building
        "manual/using-infinite-maps",
        "manual/using-infinite-maps/#creating-an-infinite-map",
        "manual/using-infinite-maps/#editing-an-infinite-map",
        
        # World Management
        "manual/worlds",
        "manual/worlds/#defining-a-world",
        "manual/worlds/#world-patterns",
        "manual/worlds/#editing-worlds",  # Advanced world management
        
        # Automation & Scripting
        "manual/using-commands",
        "manual/using-commands/#example-commands",
        "manual/automapping",  # Automated map generation
        "manual/automapping/#what-is-automapping",
        "manual/automapping/#setting-up-the-rules-file",
        
        # Export System
        "manual/export",
        "manual/export-generic",  # Generic formats
        "manual/export-custom",  # Custom export implementation
        
        # Technical Reference
        "reference/json-map-format",  # Complete format specification
        "reference/json-map-format/#map",
        "reference/json-map-format/#layer",
        "reference/json-map-format/#object",
        "reference/json-map-format/#tileset",
        "reference/json-map-format/#property",
        "reference/scripting-api",  # Scripting capabilities
        "reference/global-tile-ids",  # Core tile system
    ]
    
    # Add Map Editor URLs
    urls.add(map_editor_base)
    for url in map_editor_urls:
        urls.add(f"{map_editor_base}{url}")
    
    # Tiled Python Library documentation
    python_base = "https://tiled.readthedocs.io/en/latest/"
    python_urls = [
        # Core API Architecture
        "api/core",
        "api/core/#tiled.core.Map",  # Map architecture
        "api/core/#tiled.core.Layer",  # Layer system
        "api/core/#tiled.core.TileLayer",  # Tile management
        "api/core/#tiled.core.ObjectGroup",  # Object system
        "api/core/#tiled.core.ImageLayer",  # Image handling
        "api/core/#tiled.core.GroupLayer",  # Layer grouping
        "api/core/#tiled.core.Tileset",  # Tileset management
        "api/core/#tiled.core.Tile",  # Tile system
        "api/core/#tiled.core.Object",  # Object system
        "api/core/#tiled.core.Properties",  # Property system
        
        # I/O System Architecture
        "api/io",
        "api/io/#tiled.io.Reader",  # Base reader
        "api/io/#tiled.io.Writer",  # Base writer
        "api/io/#tiled.io.TMXReader",  # TMX format
        "api/io/#tiled.io.JSONReader",  # JSON format for RPGJS
        "api/io/#tiled.io.TMXWriter",
        "api/io/#tiled.io.JSONWriter",
        
        # Data Model Architecture
        "api/data",
        "api/data/#tiled.data.MapData",  # Map structure
        "api/data/#tiled.data.LayerData",  # Layer data
        "api/data/#tiled.data.TilesetData",  # Tileset data
        "api/data/#tiled.data.ObjectData",  # Object/NPC data
        
        # Utility System
        "api/utils",
        "api/utils/#tiled.utils.load_map",  # Loading maps
        "api/utils/#tiled.utils.save_map",  # Saving maps
        "api/utils/#tiled.utils.load_tileset",  # Loading tilesets
        "api/utils/#tiled.utils.save_tileset",  # Saving tilesets
        
        # Implementation Examples
        "examples/basic/#loading-a-map",  # Basic map operations
        "examples/basic/#saving-a-map",
        "examples/basic/#creating-a-map",  # Creating new maps
        "examples/basic/#modifying-a-map",  # Modifying existing maps
        
        # Layer Management
        "examples/layers/#working-with-layers",  # Layer manipulation
        "examples/layers/#tile-layers",  # Tile layer specifics
        "examples/layers/#object-layers",  # Object layer for NPCs/events
        "examples/layers/#image-layers",  # Background images/parallax
        "examples/layers/#group-layers",  # Organizing layers
        
        # Object Management
        "examples/objects/#creating-objects",  # Creating NPCs/events
        "examples/objects/#modifying-objects",  # Modifying NPCs/events
        "examples/objects/#object-types",  # NPC/event types
        "examples/objects/#object-properties",  # NPC/event properties
        
        # Property System
        "examples/properties/#custom-properties",  # Game logic properties
        "examples/properties/#property-types",  # Data types
        "examples/properties/#property-inheritance",  # Property inheritance
        
        # Tileset Management
        "examples/tileset/#creating-tilesets",  # Creating tilesets
        "examples/tileset/#editing-tilesets",  # Modifying tilesets
        "examples/tileset/#terrain-sets",  # Terrain system
        
        # World Management
        "examples/world/#world-files",  # Managing game worlds
        "examples/world/#world-patterns",  # World organization
        "examples/world/#world-properties",  # World configuration
    ]
    
    # Additional Python Libraries for RPGJS Integration
    python_docs = {
        # JSON Processing
        "https://docs.python.org/3/library/json.html": [
            "#json.loads",  # Parsing JSON
            "#json.dumps",  # Creating JSON
            "#encoders-and-decoders",  # Custom JSON encoding
        ],
        
        # Path Management
        "https://docs.python.org/3/library/pathlib.html": [
            "#basic-use",  # Basic path operations
            "#pure-paths",  # Path manipulation
            "#concrete-paths",  # File operations
        ],
        
        # Image Processing
        "https://pillow.readthedocs.io/en/stable/": [
            "reference/Image.html",  # Image manipulation
            "reference/ImageDraw.html",  # Drawing shapes
            "reference/ImageEnhance.html",  # Image effects
        ],
        
        # Async Operations
        "https://docs.python.org/3/library/asyncio.html": [
            "#coroutines",  # Async basics
            "#tasks",  # Task management
            "#streams",  # Async I/O
        ],
        
        # Data Structures
        "https://docs.python.org/3/library/collections.html": [
            "#collections.defaultdict",  # Automatic dictionaries
            "#collections.OrderedDict",  # Ordered maps
            "#collections.namedtuple",  # Structured data
        ],
        
        # File System Operations
        "https://docs.python.org/3/library/shutil.html": [
            "#directory-and-files-operations",  # File operations
            "#archiving-operations",  # Asset packaging
        ],
        
        # Configuration Management
        "https://docs.python.org/3/library/configparser.html": [
            "#quick-start",  # Basic config
            "#supported-datatypes",  # Data types
            "#interpolation-of-values",  # Variable substitution
        ],
        
        # Logging
        "https://docs.python.org/3/library/logging.html": [
            "#logging-levels",  # Log levels
            "#logging-to-files",  # File logging
            "#formatting-styles",  # Log formatting
        ],
        
        # Testing
        "https://docs.pytest.org/en/stable/": [
            "getting-started.html",  # Basic testing
            "fixture.html",  # Test fixtures
            "parametrize.html",  # Parameterized tests
        ]
    }
    
    # Add Python Library URLs
    for url in python_urls:
        urls.add(f"{python_base}{url}")
    
    # Add Additional Python Library URLs
    for base_url, paths in python_docs.items():
        if not paths:
            urls.add(base_url)
        else:
            for path in paths:
                urls.add(f"{base_url}{path}")
    
    print(f"Found URLs:\n" + "\n".join(sorted(urls)))
    return list(urls)

async def main():
    """Main function to crawl and process Tiled documentation."""
    print("Getting Tiled documentation URLs...")
    urls = await get_tiled_docs_urls()
    
    if not urls:
        print("No URLs found!")
        return
    
    print(f"Found {len(urls)} URLs to process")
    print("Starting crawl...")
    await crawl_parallel(urls)
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
