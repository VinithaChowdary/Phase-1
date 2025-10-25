import os
import sys
import json
import asyncio
import requests
from xml.etree import ElementTree
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv
from colorama import Fore, Back, Style, init

# Initialize colorama for Windows support
init(autoreset=True)

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from openai import AsyncOpenAI
from supabase import create_client, Client

load_dotenv()

from sentence_transformers import SentenceTransformer

# Logging helpers
def log_info(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.CYAN}[{timestamp}] ℹ️  {message}{Style.RESET_ALL}")

def log_success(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.GREEN}[{timestamp}] ✅ {message}{Style.RESET_ALL}")

def log_warning(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.YELLOW}[{timestamp}] ⚠️  {message}{Style.RESET_ALL}")

def log_error(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.RED}[{timestamp}] ❌ {message}{Style.RESET_ALL}")

def log_crawl(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Fore.MAGENTA}[{timestamp}] 🕷️  {message}{Style.RESET_ALL}")

def log_progress(current: int, total: int, message: str = ""):
    timestamp = datetime.now().strftime("%H:%M:%S")
    percent = (current / total * 100) if total > 0 else 0
    bar = "█" * int(percent / 2) + "░" * (50 - int(percent / 2))
    print(f"{Fore.WHITE}{Back.BLUE}[{timestamp}] 📊 [{bar}] {percent:.1f}% {message}{Style.RESET_ALL}")
# Configure DeepSeek API
_deepseek_key = os.getenv("DEEPSEEK_API_KEY")
_deepseek_base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

log_info("Loading embedding model...")
# Load local embedding model
_embedder = SentenceTransformer(os.getenv('EMBEDDING_MODEL_NAME', 'sentence-transformers/all-MiniLM-L6-v2'))
log_success(f"Embedding model loaded: {_embedder}")

log_info("Connecting to Supabase...")
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)
log_success("Supabase client initialized")

log_info("Initializing OpenAI client...")
# Async client for DeepSeek chat and completions
openai_client = AsyncOpenAI(base_url=_deepseek_base, api_key=_deepseek_key)
log_success("OpenAI client initialized")

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
    log_info(f"Chunking text of length {len(text)} with chunk_size={chunk_size}")
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

    log_success(f"Created {len(chunks)} chunks")
    return chunks

async def get_title_and_summary(chunk: str, url: str) -> Dict[str, str]:
    """Extract title and summary using GPT-4."""
    system_prompt = """You are an AI that extracts titles and summaries from documentation chunks.
    Return a JSON object with 'title' and 'summary' keys.
    For the title: If this seems like the start of a document, extract its title. If it's a middle chunk, derive a descriptive title.
    For the summary: Create a concise summary of the main points in this chunk.
    Keep both title and summary concise but informative."""
    
    try:
        log_info(f"Extracting title and summary for URL: {url[:50]}...")
        response = await openai_client.chat.completions.create(
            model=os.getenv("PRIMARY_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"URL: {url}\n\nContent:\n{chunk[:1000]}..."}  # Send first 1000 chars for context
            ],
            response_format={ "type": "json_object" }
        )
        result = json.loads(response.choices[0].message.content)
        log_success(f"Title: {result.get('title', 'N/A')[:50]}...")
        return result
    except Exception as e:
        log_error(f"Error getting title and summary: {e}")
        return {"title": "Error processing title", "summary": "Error processing summary"}

async def get_embedding(text: str) -> List[float]:
    """Get embedding vector using local SentenceTransformer model."""
    try:
        vec = _embedder.encode(text, normalize_embeddings=True)
        return vec.tolist()
    except Exception as e:
        log_error(f"Error getting embedding: {e}")
        dim = getattr(_embedder, 'get_sentence_embedding_dimension', lambda: len(vec))()
        return [0.0] * dim

async def process_chunk(chunk: str, chunk_number: int, url: str) -> ProcessedChunk:
    """Process a single chunk of text."""
    log_info(f"Processing chunk {chunk_number} for {url[:50]}...")
    
    # Get title and summary
    extracted = await get_title_and_summary(chunk, url)
    
    # Get embedding
    embedding = await get_embedding(chunk)
    
    # Create metadata
    metadata = {
        "source": "pydantic_ai_docs",
        "chunk_size": len(chunk),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "url_path": urlparse(url).path
    }
    
    log_success(f"Chunk {chunk_number} processed")
    
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
        
        result = supabase.table("site_pages").insert(data).execute()
        log_success(f"✓ Inserted chunk {chunk.chunk_number} for {chunk.url[:50]}...")
        return result
    except Exception as e:
        log_error(f"Error inserting chunk: {e}")
        return None

async def process_and_store_document(url: str, markdown: str):
    """Process a document and store its chunks in parallel."""
    log_info(f"📄 Processing document: {url}")
    
    # Split into chunks
    chunks = chunk_text(markdown)
    log_info(f"Document split into {len(chunks)} chunks")
    
    # Process chunks in parallel
    log_info("Processing chunks in parallel...")
    tasks = [
        process_chunk(chunk, i, url) 
        for i, chunk in enumerate(chunks)
    ]
    processed_chunks = await asyncio.gather(*tasks)
    log_success(f"All {len(processed_chunks)} chunks processed")
    
    # Store chunks in parallel
    log_info("Storing chunks in database...")
    insert_tasks = [
        insert_chunk(chunk) 
        for chunk in processed_chunks
    ]
    await asyncio.gather(*insert_tasks)
    log_success(f"✅ Document fully processed and stored: {url}")

async def crawl_parallel(urls: List[str], max_concurrent: int = 5):
    """Crawl multiple URLs in parallel with a concurrency limit."""
    log_crawl(f"Starting parallel crawl of {len(urls)} URLs (max concurrent: {max_concurrent})")
    
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    # Create the crawler instance
    log_info("Initializing web crawler...")
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()
    log_success("Crawler started")

    try:
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        completed = 0
        
        async def process_url(url: str):
            nonlocal completed
            async with semaphore:
                log_crawl(f"Crawling: {url}")
                result = await crawler.arun(
                    url=url,
                    config=crawl_config,
                    session_id="session1"
                )
                if result.success:
                    log_success(f"Successfully crawled: {url}")
                    await process_and_store_document(url, result.markdown_v2.raw_markdown)
                else:
                    log_error(f"Failed: {url} - Error: {result.error_message}")
                
                completed += 1
                log_progress(completed, len(urls), f"({completed}/{len(urls)} URLs)")
        
        # Process all URLs in parallel with limited concurrency
        await asyncio.gather(*[process_url(url) for url in urls])
        log_success(f"🎉 All {len(urls)} URLs processed!")
    finally:
        log_info("Closing crawler...")
        await crawler.close()
        log_success("Crawler closed")

def get_pydantic_ai_docs_urls() -> List[str]:
    """Get URLs from Pydantic AI docs sitemap."""
    sitemap_url = "https://ai.pydantic.dev/sitemap.xml"
    log_info(f"Fetching sitemap from: {sitemap_url}")
    try:
        response = requests.get(sitemap_url)
        response.raise_for_status()
        
        # Parse the XML
        root = ElementTree.fromstring(response.content)
        
        # Extract all URLs from the sitemap
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
        
        log_success(f"Found {len(urls)} URLs in sitemap")
        return urls
    except Exception as e:
        log_error(f"Error fetching sitemap: {e}")
        return []

async def main():
    log_info("=" * 60)
    log_info("🕷️  PYDANTIC AI DOCUMENTATION CRAWLER")
    log_info("=" * 60)
    
    # Get URLs from Pydantic AI docs
    urls = get_pydantic_ai_docs_urls()
    if not urls:
        log_error("No URLs found to crawl")
        return
    
    log_info(f"📚 Found {len(urls)} URLs to crawl")
    log_info("Starting crawl process...")
    log_info("=" * 60)
    
    await crawl_parallel(urls)
    
    log_info("=" * 60)
    log_success("✨ Crawling complete!")
    log_info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
