from __future__ import annotations as _annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

import os
import logfire
import asyncio
from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI
from supabase import Client
from sentence_transformers import SentenceTransformer

load_dotenv()
logfire.configure(send_to_logfire='if-token-present')

# --- Unified OpenAI-compatible config (one place) -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or ""
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# Export for libs that read these envs implicitly
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_BASE_URL"] = OPENAI_BASE_URL

model = OpenAIModel(
    model_name=LLM_MODEL,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

# Local embedding model (kept)
_embedder = SentenceTransformer(os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"))

@dataclass
class PydanticAIDeps:
    supabase: Client
    openai_client: AsyncOpenAI

# --- Strict planning model (structured output) -------------------------------
class PlanAction(BaseModel):
    """
    First step: the assistant MUST emit this object (via the tool call below)
    to declare its next concrete action BEFORE any conversational text.
    """
    step: Literal["plan_rag", "plan_list_pages", "plan_fetch_page"] = Field(
        description="The next action to take."
    )
    rag_query: Optional[str] = Field(
        default=None,
        description="Required when step == 'plan_rag': the semantic search query."
    )
    page_url: Optional[HttpUrl] = Field(
        default=None,
        description="Required when step == 'plan_fetch_page': a full docs URL to fetch."
    )

    def validate_semantics(self) -> None:
        if self.step == "plan_rag" and not self.rag_query:
            raise ValueError("rag_query is required when step='plan_rag'")
        if self.step == "plan_fetch_page" and not self.page_url:
            raise ValueError("page_url is required when step='plan_fetch_page'")


system_prompt = """
You are an expert in the Pydantic AI framework. You have tools to retrieve and browse documentation.

CRITICAL PROTOCOL — DO NOT VIOLATE:
1) Do not produce conversational text until AFTER you have executed at least one documentation tool.
2) Your FIRST action on every new user problem must be to emit a structured plan by calling the tool
   `propose_next_action` with a valid PlanAction object. After that, immediately execute the plan by
   calling one or more of: `retrieve_relevant_documentation`, `list_documentation_pages`, `get_page_content`.
3) Keep planning lightweight and focused on the exact next step (RAG, list, or fetch).
4) Only after at least one tool result is available should you compose explanatory or code output.

WORKFLOW:
- Call `propose_next_action` → then call the chosen documentation tool(s) → then synthesize the final answer.
- Use multiple documentation tool calls when helpful; never rely on a single chunk if building an agent from scratch.
- Be explicit about what you used: cite page titles/URLs in your natural-language answer (no markdown links required).
- If you can’t find something in docs, state that clearly and propose a fallback or reasonable assumption.

DELIVERABLES WHEN BUILDING AN AGENT:
Return complete files:
- agent.py
- agent_tools.py
- agent_prompts.py
- .env.example (with comments)
- requirements.txt (top-level packages only, no pins)
"""

pydantic_ai_coder = Agent(
    model,
    system_prompt=system_prompt,
    deps_type=PydanticAIDeps,
    retries=2,
)

# --- Helper: local embedding -------------------------------------------------
async def get_embedding(text: str, _unused_openai_client: AsyncOpenAI | None = None) -> List[float]:
    try:
        vec = _embedder.encode(text, normalize_embeddings=True)
        return vec.tolist()
    except Exception as e:
        print(f"Error getting embedding: {e}")
        dim = getattr(_embedder, 'get_sentence_embedding_dimension', lambda: 384)()
        return [0.0] * dim

# --- Planning tool: MUST be called first ------------------------------------
@pydantic_ai_coder.tool
async def propose_next_action(ctx: RunContext[PydanticAIDeps], plan: PlanAction) -> str:
    """
    The assistant MUST call this tool first to declare its next step.
    This prevents premature conversational text and drives tool execution.
    """
    try:
        plan.validate_semantics()
        return f"ACK: planning {plan.step}"
    except Exception as e:
        return f"Invalid plan: {e}"

# --- Documentation tools (unchanged logic; small cleanups) -------------------
@pydantic_ai_coder.tool
async def retrieve_relevant_documentation(ctx: RunContext[PydanticAIDeps], user_query: str) -> str:
    """
    RAG: Return up to 5 most relevant documentation chunks for `user_query`.
    """
    try:
        query_embedding = await get_embedding(user_query)
        result = ctx.deps.supabase.rpc(
            "match_site_pages",
            {"query_embedding": query_embedding, "match_count": 5, "filter": {"source": "pydantic_ai_docs"}},
        ).execute()

        data = getattr(result, "data", None)
        if not data:
            return "No relevant documentation found."

        formatted_chunks = []
        for doc in data:
            title = doc.get("title", "Untitled")
            content = doc.get("content", "")
            formatted_chunks.append(f"# {title}\n\n{content}")

        return "\n\n---\n\n".join(formatted_chunks)
    except Exception as e:
        print(f"Error retrieving documentation: {e}")
        return f"Error retrieving documentation: {str(e)}"

@pydantic_ai_coder.tool
async def list_documentation_pages(ctx: RunContext[PydanticAIDeps]) -> List[str]:
    """
    List all Pydantic AI documentation URLs available in Supabase.
    """
    try:
        result = (
            ctx.deps.supabase.from_("site_pages")
            .select("url")
            .eq("metadata->>source", "pydantic_ai_docs")
            .execute()
        )
        data = getattr(result, "data", None) or []
        return sorted({doc["url"] for doc in data if "url" in doc})
    except Exception as e:
        print(f"Error retrieving documentation pages: {e}")
        return []

@pydantic_ai_coder.tool
async def get_page_content(ctx: RunContext[PydanticAIDeps], url: str) -> str:
    """
    Combine all chunks for a given page URL into a single document.
    """
    try:
        result = (
            ctx.deps.supabase.from_("site_pages")
            .select("title, content, chunk_number")
            .eq("url", url)
            .eq("metadata->>source", "pydantic_ai_docs")
            .order("chunk_number")
            .execute()
        )
        data = getattr(result, "data", None) or []
        if not data:
            return f"No content found for URL: {url}"

        page_title = (data[0].get("title") or "Untitled").split(" - ")[0]
        parts = [f"# {page_title}\n"]
        for chunk in data:
            parts.append(chunk.get("content", ""))

        return "\n\n".join(parts)
    except Exception as e:
        print(f"Error retrieving page content: {e}")
        return f"Error retrieving page content: {str(e)}"
