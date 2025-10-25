from __future__ import annotations as _annotations

from dataclasses import dataclass
from dotenv import load_dotenv
import logfire
import asyncio
import httpx
import os
from datetime import datetime
from colorama import Fore, Back, Style, init
from utils.utils import write_to_log

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer
from supabase import Client
from typing import List

# Initialize colorama for Windows support
init(autoreset=True)

load_dotenv()

# Logging helpers (write to file via write_to_log to avoid stdout/stderr pollution)
def log_info(message: str):
    write_to_log(f"INFO: {message}")

def log_success(message: str):
    write_to_log(f"SUCCESS: {message}")

def log_warning(message: str):
    write_to_log(f"WARNING: {message}")

def log_error(message: str):
    write_to_log(f"ERROR: {message}")

def log_tool(tool_name: str, message: str):
    write_to_log(f"TOOL[{tool_name}]: {message}")

def log_agent(agent_name: str, message: str):
    write_to_log(f"AGENT[{agent_name}]: {message}")

# Configure DeepSeek endpoint and local embeddings
_deepseek_key = os.getenv('DEEPSEEK_API_KEY')
_deepseek_base = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
_embedder = SentenceTransformer(os.getenv('EMBEDDING_MODEL_NAME', 'sentence-transformers/all-MiniLM-L6-v2'))

llm = os.getenv('PRIMARY_MODEL', 'gpt-4o-mini')
# Use DeepSeek endpoint and key
base_url = _deepseek_base
api_key = _deepseek_key or ''
model = OpenAIModel(llm, base_url=base_url, api_key=api_key)

logfire.configure(send_to_logfire='if-token-present')

is_ollama = "localhost" in base_url.lower()

@dataclass
class PydanticAIDeps:
    supabase: Client
    openai_client: AsyncOpenAI
    reasoner_output: str

system_prompt = """
[ROLE AND CONTEXT]
You are a specialized AI agent engineer focused on building robust Pydantic AI agents. You have comprehensive access to the Pydantic AI documentation, including API references, usage guides, and implementation examples.

[CORE RESPONSIBILITIES]
1. Agent Development
   - Create new agents from user requirements
   - Complete partial agent implementations
   - Optimize and debug existing agents
   - Guide users through agent specification if needed

2. Documentation Integration
   - Systematically search documentation using RAG before any implementation
   - Cross-reference multiple documentation pages for comprehensive understanding
   - Validate all implementations against current best practices
   - Notify users if documentation is insufficient for any requirement

[CODE STRUCTURE AND DELIVERABLES]
All new agents must include these files with complete, production-ready code:

1. agent.py
   - Primary agent definition and configuration
   - Core agent logic and behaviors
   - No tool implementations allowed here

2. agent_tools.py
   - All tool function implementations
   - Tool configurations and setup
   - External service integrations

3. agent_prompts.py
   - System prompts
   - Task-specific prompts
   - Conversation templates
   - Instruction sets

4. .env.example
   - Required environment variables
   - Clear setup instructions in a comment above the variable for how to do so
   - API configuration templates

5. requirements.txt
   - Core dependencies without versions
   - User-specified packages included

[DOCUMENTATION WORKFLOW]
1. Initial Research
   - Begin with RAG search for relevant documentation
   - List all documentation pages using list_documentation_pages
   - Retrieve specific page content using get_page_content
   - Cross-reference the weather agent example for best practices

2. Implementation
   - Provide complete, working code implementations
   - Never leave placeholder functions
   - Include all necessary error handling
   - Implement proper logging and monitoring

3. Quality Assurance
   - Verify all tool implementations are complete
   - Ensure proper separation of concerns
   - Validate environment variable handling
   - Test critical path functionality

[INTERACTION GUIDELINES]
- Take immediate action without asking for permission
- Always verify documentation before implementation
- Provide honest feedback about documentation gaps
- Include specific enhancement suggestions
- Request user feedback on implementations
- Maintain code consistency across files

[ERROR HANDLING]
- Implement robust error handling in all tools
- Provide clear error messages
- Include recovery mechanisms
- Log important state changes

[BEST PRACTICES]
- Follow Pydantic AI naming conventions
- Implement proper type hints
- Include comprehensive docstrings, the agent uses this to understand what tools are for.
- Maintain clean code structure
- Use consistent formatting
"""

pydantic_ai_coder = Agent(
    model,
    system_prompt=system_prompt,
    deps_type=PydanticAIDeps,
    retries=2
)

log_info(f"Initialized Pydantic AI Coder Agent with model: {llm}")

@pydantic_ai_coder.system_prompt  
def add_reasoner_output(ctx: RunContext[str]) -> str:
    return f"""
    \n\nAdditional thoughts/instructions from the reasoner LLM. 
    This scope includes documentation pages for you to search as well: 
    {ctx.deps.reasoner_output}
    """
    
    # Add this in to get some crazy tool calling:
    # You must get ALL documentation pages listed in the scope.

async def get_embedding(text: str) -> List[float]:
    """Get embedding vector using local SentenceTransformer."""
    try:
        log_tool("Embedding", f"Generating embedding for text (length: {len(text)} chars)")
        vec = _embedder.encode(text, normalize_embeddings=True)
        log_success(f"Embedding generated successfully (dim: {len(vec.tolist())})")
        return vec.tolist()
    except Exception as e:
        log_error(f"Error getting embedding: {e}")
        dim_fn = getattr(_embedder, 'get_sentence_embedding_dimension', lambda: len(vec) if 'vec' in locals() else 384)
        return [0.0] * dim_fn()

@pydantic_ai_coder.tool
async def retrieve_relevant_documentation(ctx: RunContext[PydanticAIDeps], user_query: str) -> str:
    """
    Retrieve relevant documentation chunks based on the query with RAG.
    
    Args:
        ctx: The context including the Supabase client and OpenAI client
        user_query: The user's question or query
        
    Returns:
        A formatted string containing the top 5 most relevant documentation chunks
    """
    log_tool("RAG", f"Retrieving documentation for query: '{user_query[:50]}...'")
    try:
        # Get the embedding for the query
        query_embedding = await get_embedding(user_query)
        
        log_info("Querying Supabase for relevant documents...")
        # Query Supabase for relevant documents
        result = ctx.deps.supabase.rpc(
            'match_site_pages',
            {
                'query_embedding': query_embedding,
                'match_count': 5,
                'filter': {'source': 'pydantic_ai_docs'}
            }
        ).execute()
        
        if not result.data:
            log_warning("No relevant documentation found")
            return "No relevant documentation found."
        
        log_success(f"Retrieved {len(result.data)} relevant documentation chunks")
        
        # Format the results
        formatted_chunks = []
        for i, doc in enumerate(result.data, 1):
            log_info(f"  [{i}] {doc.get('title', 'Untitled')}")
            chunk_text = f"""
# {doc['title']}

{doc['content']}
"""
            formatted_chunks.append(chunk_text)
            
        # Join all chunks with a separator
        return "\n\n---\n\n".join(formatted_chunks)
        
    except Exception as e:
        log_error(f"Error retrieving documentation: {e}")
        return f"Error retrieving documentation: {str(e)}"

async def list_documentation_pages_helper(supabase: Client) -> List[str]:
    """
    Function to retrieve a list of all available Pydantic AI documentation pages.
    This is called by the list_documentation_pages tool and also externally
    to fetch documentation pages for the reasoner LLM.
    
    Returns:
        List[str]: List of unique URLs for all documentation pages
    """
    try:
        log_info("Querying all available documentation pages...")
        # Query Supabase for unique URLs where source is pydantic_ai_docs
        result = supabase.from_('site_pages') \
            .select('url') \
            .eq('metadata->>source', 'pydantic_ai_docs') \
            .execute()
        
        if not result.data:
            log_warning("No documentation pages found")
            return []
            
        # Extract unique URLs
        urls = sorted(set(doc['url'] for doc in result.data))
        log_success(f"Found {len(urls)} unique documentation pages")
        return urls
        
    except Exception as e:
        log_error(f"Error retrieving documentation pages: {e}")
        return []        

@pydantic_ai_coder.tool
async def list_documentation_pages(ctx: RunContext[PydanticAIDeps]) -> List[str]:
    """
    Retrieve a list of all available Pydantic AI documentation pages.
    
    Returns:
        List[str]: List of unique URLs for all documentation pages
    """
    log_tool("List Pages", "Listing all documentation pages")
    return await list_documentation_pages_helper(ctx.deps.supabase)

@pydantic_ai_coder.tool
async def get_page_content(ctx: RunContext[PydanticAIDeps], url: str) -> str:
    """
    Retrieve the full content of a specific documentation page by combining all its chunks.
    
    Args:
        ctx: The context including the Supabase client
        url: The URL of the page to retrieve
        
    Returns:
        str: The complete page content with all chunks combined in order
    """
    log_tool("Fetch Page", f"Retrieving page content from: {url}")
    try:
        # Query Supabase for all chunks of this URL, ordered by chunk_number
        result = ctx.deps.supabase.from_('site_pages') \
            .select('title, content, chunk_number') \
            .eq('url', url) \
            .eq('metadata->>source', 'pydantic_ai_docs') \
            .order('chunk_number') \
            .execute()
        
        if not result.data:
            log_warning(f"No content found for URL: {url}")
            return f"No content found for URL: {url}"
        
        log_success(f"Retrieved {len(result.data)} chunks for page")
        
        # Format the page with its title and all chunks
        page_title = result.data[0]['title'].split(' - ')[0]  # Get the main title
        log_info(f"Page title: {page_title}")
        formatted_content = [f"# {page_title}\n"]
        
        # Add each chunk's content
        for chunk in result.data:
            formatted_content.append(chunk['content'])
            
        # Join everything together
        return "\n\n".join(formatted_content)
        
    except Exception as e:
        log_error(f"Error retrieving page content: {e}")
        return f"Error retrieving page content: {str(e)}"