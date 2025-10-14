from __future__ import annotations
from typing import Literal, TypedDict, Any
import asyncio
import os
import json

import streamlit as st
import logfire
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import AsyncOpenAI

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    UserPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    RetryPromptPart,
    ModelMessagesTypeAdapter,
)
# Streaming/event imports with graceful fallback for older versions
try:
    from pydantic_ai import (
        AgentStreamEvent,
        FunctionToolCallEvent,
        FunctionToolResultEvent,
        PartDeltaEvent,
        PartStartEvent,
        TextPartDelta,
        ToolCallPartDelta,
        FinalResultEvent,
        RunContext,
    )
except Exception:  # pragma: no cover - compatibility layer
    from typing import Any

    AgentStreamEvent = Any  # type: ignore
    FunctionToolCallEvent = None  # type: ignore
    FunctionToolResultEvent = None  # type: ignore
    PartDeltaEvent = None  # type: ignore
    PartStartEvent = None  # type: ignore
    TextPartDelta = None  # type: ignore
    ToolCallPartDelta = None  # type: ignore
    FinalResultEvent = None  # type: ignore
    RunContext = Any  # type: ignore

from pydantic_ai_coder import pydantic_ai_coder, PydanticAIDeps

# -----------------------------------------------------------------------------
# Unified config (matches pydantic_ai_coder.py)
# -----------------------------------------------------------------------------
load_dotenv()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or ""
openai_client = AsyncOpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)

logfire.configure(send_to_logfire="never")

class ChatMessage(TypedDict):
    role: Literal["user", "model"]
    timestamp: str
    content: str

# -----------------------------------------------------------------------------
# Rendering helpers
# -----------------------------------------------------------------------------
def display_message_part(part: Any) -> None:
    """Render different part types in Streamlit."""
    kind = getattr(part, "part_kind", None)
    content = getattr(part, "content", None)

    if kind == "system-prompt":
        with st.chat_message("system"):
            st.markdown(f"**System**: {content}")
    elif kind == "user-prompt":
        with st.chat_message("user"):
            st.markdown(content)
    elif kind == "text":
        with st.chat_message("assistant"):
            st.markdown(content)
    elif kind == "tool-call":
        # Tool call details
        name = getattr(part, "tool_name", "tool")
        args = getattr(part, "args", {})
        with st.chat_message("assistant"):
            st.markdown(f"🛠️ **Calling tool:** `{name}`")
            st.code(json.dumps(args, indent=2))
    elif kind == "tool-return":
        name = getattr(part, "tool_name", "tool")
        result = getattr(part, "result", None)
        with st.chat_message("assistant"):
            st.markdown(f"📥 **Tool result from:** `{name}`")
            if isinstance(result, (dict, list)):
                st.code(json.dumps(result, indent=2))
            else:
                st.markdown(result if result else "_(empty)_")

# -----------------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------------
async def run_agent_with_streaming(user_input: str) -> None:
    """
    Non-streaming path: call Agent.run() and display the final output.
    Also refresh message_history so future turns keep context.
    """
    deps = PydanticAIDeps(supabase=supabase, openai_client=openai_client)

    def _extract_output_text(run_result: Any) -> str:
        # Try common property
        txt = getattr(run_result, "output", None)
        if isinstance(txt, str) and txt:
            return txt
        # Build from messages as fallback
        messages = []
        try:
            messages = run_result.all_messages()
        except Exception:
            pass
        pieces: list[str] = []
        for m in messages:
            if isinstance(m, ModelResponse):
                for p in getattr(m, "parts", []):
                    if getattr(p, "part_kind", None) == "text":
                        c = getattr(p, "content", "")
                        if isinstance(c, str):
                            pieces.append(c)
        joined = "".join(pieces).strip()
        return joined or "(no text output)"

    with st.spinner("Thinking..."):
        result = await pydantic_ai_coder.run(
            user_input,
            deps=deps,
            # Exclude the last user message we just appended to avoid duplication
            message_history=st.session_state.messages[:-1],
        )

    # Show final model output immediately
    with st.chat_message("assistant"):
        st.markdown(_extract_output_text(result))

    # Update session history for next turn
    try:
        st.session_state.messages = result.new_messages()
    except Exception:
        # Fallback to full messages if new_messages is unavailable
        try:
            st.session_state.messages = result.all_messages()
        except Exception:
            # Last resort: append final text part only
            st.session_state.messages.append(ModelResponse(parts=[TextPart(content=str(result.output))]))

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
async def main() -> None:
    st.title("Archon - Agent Builder (V1 RAG)")
    st.write("Describe an AI agent you want to build. I’ll help you code it with Pydantic AI.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Render history
    for msg in st.session_state.messages:
        if isinstance(msg, (ModelRequest, ModelResponse)):
            for part in msg.parts:
                display_message_part(part)

    # Chat input
    user_input = st.chat_input("What do you want to build today?")
    if user_input:
        # Append user turn
        st.session_state.messages.append(ModelRequest(parts=[UserPromptPart(content=user_input)]))
        with st.chat_message("user"):
            st.markdown(user_input)
        # run_agent_with_streaming renders the assistant response itself
        await run_agent_with_streaming(user_input)

if __name__ == "__main__":
    asyncio.run(main())
