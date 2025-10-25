from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai import Agent, RunContext
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated, List, Any
from langgraph.config import get_stream_writer
from langgraph.types import Command
from dotenv import load_dotenv
from openai import AsyncOpenAI
from supabase import Client
import logfire
import os
from openai import BadRequestError
from datetime import datetime
from colorama import Fore, Back, Style, init

# Initialize colorama for Windows support
init(autoreset=True)

# Import the message classes from Pydantic AI
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter
)

from .pydantic_ai_coder import pydantic_ai_coder, PydanticAIDeps, list_documentation_pages_helper

# Logging helpers
from utils.utils import write_to_log

# Logging helpers now write to workbench/logs.txt to avoid printing to stdout
def _fmt(msg_type: str, message: str) -> str:
    timestamp = datetime.now().strftime("%H:%M:%S")
    return f"[{timestamp}] {msg_type} {message}"

def log_info(message: str):
    write_to_log(_fmt("INFO", message))

def log_success(message: str):
    write_to_log(_fmt("SUCCESS", message))

def log_warning(message: str):
    write_to_log(_fmt("WARNING", message))

def log_error(message: str):
    write_to_log(_fmt("ERROR", message))

def log_node(node_name: str, message: str):
    write_to_log(_fmt("NODE", f"[{node_name}] {message}"))

def log_agent(agent_name: str, message: str):
    write_to_log(_fmt("AGENT", f"[{agent_name}] {message}"))

def log_state(message: str):
    write_to_log(_fmt("STATE", message))

def log_step(message: str):
    """Major step logging with a distinct tag to differentiate workflow steps."""
    write_to_log(_fmt("STEP", message))

# Load environment variables
load_dotenv()

log_step("🚀 Initializing Agentic Workflow System...")

# Configure DeepSeek as OpenAI-compatible endpoint
# Use the DEEPSEEK URL/env names requested in the workspace
_deepseek_key = os.getenv('DEEPSEEK_API_KEY')
_deepseek_base = os.getenv('DEEPSEEK_URL', 'https://api.deepseek.com')
# configure DeepSeek credentials
# (no need to set OPENAI_* vars since we pass base_url/api_key directly)

# Configure logfire to suppress warnings (optional)
logfire.configure(send_to_logfire='never')

base_url = _deepseek_base
api_key = _deepseek_key or ''
is_ollama = "localhost" in base_url.lower()
# Default to Deepseek-provided models unless overridden by environment
reasoner_llm_model = os.getenv('REASONER_MODEL', 'deepseek-reasoner')

log_info(f"Initializing Reasoner Agent with model: {reasoner_llm_model}")
reasoner = Agent(  
    OpenAIModel(reasoner_llm_model, base_url=base_url, api_key=api_key),
    system_prompt='You are an expert at coding AI agents with Pydantic AI and defining the scope for doing so.',  
)
log_success("Reasoner Agent initialized")

primary_llm_model = os.getenv('PRIMARY_MODEL', 'deepseek-chat')

log_info(f"Initializing Router Agent with model: {primary_llm_model}")
router_agent = Agent(  
    OpenAIModel(primary_llm_model, base_url=base_url, api_key=api_key),
    system_prompt='Your job is to route the user message either to the end of the conversation or to continue coding the AI agent.',  
)
log_success("Router Agent initialized")

log_info(f"Initializing End Conversation Agent with model: {primary_llm_model}")
end_conversation_agent = Agent(  
    OpenAIModel(primary_llm_model, base_url=base_url, api_key=api_key),
    system_prompt='Your job is to end a conversation for creating an AI agent by giving instructions for how to execute the agent and they saying a nice goodbye to the user.',  
)
log_success("End Conversation Agent initialized")

openai_client=None

if is_ollama:
    log_info("Using Ollama endpoint for OpenAI client")
    openai_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
else:
    log_info("Using DeepSeek endpoint for OpenAI client")
    openai_client = AsyncOpenAI(base_url=_deepseek_base, api_key=_deepseek_key)

log_info("Connecting to Supabase...")
supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)
log_success("Supabase client initialized")

# Define state schema
class AgentState(TypedDict):
    latest_user_message: str
    messages: Annotated[List[bytes], lambda x, y: x + y]
    scope: str

# Scope Definition Node with Reasoner LLM
async def define_scope_with_reasoner(state: AgentState):
    log_node("Scope Definition", "Starting scope definition process")
    log_state(f"User message: {state['latest_user_message'][:100]}...")
    
    # First, get the documentation pages so the reasoner can decide which ones are necessary
    log_info("Fetching documentation pages list...")
    documentation_pages = await list_documentation_pages_helper(supabase)
    documentation_pages_str = "\n".join(documentation_pages)
    log_success(f"Retrieved {len(documentation_pages)} documentation pages")

    # Then, use the reasoner to define the scope
    prompt = f"""
    User AI Agent Request: {state['latest_user_message']}
    
    Create detailed scope document for the AI agent including:
    - Architecture diagram
    - Core components
    - External dependencies
    - Testing strategy

    Also based on these documentation pages available:

    {documentation_pages_str}

    Include a list of documentation pages that are relevant to creating this agent for the user in the scope document.
    """

    log_agent("Reasoner", "Running reasoner to define scope...")
    result = await reasoner.run(prompt)
    scope = result.data
    log_success(f"Scope defined (length: {len(scope)} chars)")

    # Save the scope to a file
    scope_path = os.path.join("workbench", "scope.md")
    os.makedirs("workbench", exist_ok=True)

    with open(scope_path, "w", encoding="utf-8") as f:
        f.write(scope)
    
    log_success(f"Scope saved to {scope_path}")
    log_state("Scope definition complete, updating state")
    
    return {"scope": scope}

# Coding Node with Feedback Handling
async def coder_agent(state: AgentState, writer):
    log_node("Coder Agent", "Starting code generation process")
    log_state(f"Message history length: {len(state.get('messages', []))} messages")
    
    # Prepare dependencies
    deps = PydanticAIDeps(
        supabase=supabase,
        openai_client=openai_client,
        reasoner_output=state['scope']
    )
    log_info("Dependencies prepared with scope context")

    # Get the message history into the format for Pydantic AI
    message_history: list[ModelMessage] = []
    for message_row in state['messages']:
        message_history.extend(ModelMessagesTypeAdapter.validate_json(message_row))
    log_info(f"Loaded {len(message_history)} messages from history")

    # Run the agent and return full response immediately
    try:
        log_agent("Coder", f"Running coder agent with message: '{state['latest_user_message'][:100]}...'")
        result = await pydantic_ai_coder.run(
            state['latest_user_message'], deps=deps, message_history=message_history
        )
        log_success("Coder agent completed successfully")
    except BadRequestError as e:
        # Handle OpenAI-compatible providers strict tool call protocol errors
        msg = str(e)
        if "tool_calls" in msg and "insufficient tool messages" in msg:
            log_warning("Tool call sequencing issue detected, retrying with clean history...")
            # Fallback: retry with a clean history to ensure the tool-call sequence is valid
            try:
                writer("[note] Recovering from tool-calls sequencing issue. Retrying with a fresh context...\n")
            except Exception:
                # writer may not accept strings in some stream modes; ignore
                pass
            result = await pydantic_ai_coder.run(
                state['latest_user_message'], deps=deps, message_history=[]
            )
            log_success("Retry successful with clean history")
        else:
            log_error(f"BadRequestError: {msg}")
            raise

    # Output complete response
    log_info("Streaming result to writer...")
    writer(result.data)
    log_state("Updating state with new messages")

    # print(ModelMessagesTypeAdapter.validate_json(result.new_messages_json()))

    return {"messages": [result.new_messages_json()]}

# Interrupt the graph to get the user's next message
async def get_next_user_message(*args):
    """
    Accepts either:
      - A Command(resume=...) alone, or
      - (state_dict, Command(resume=...)), or
      - A state_dict without Command.
    Returns a dict updating 'latest_user_message'.
    """
    log_node("Get User Message", "Waiting for next user message...")
    from langgraph.types import Command as _Cmd
    resume = None
    # Check for Command in args
    for arg in args:
        if isinstance(arg, _Cmd):
            resume = arg.resume
            break
    # If no Command, check for state dict
    if resume is None and args:
        state = args[0]
        if isinstance(state, dict) and 'latest_user_message' in state:
            resume = state.get('latest_user_message')
    
    log_info(f"Received user message: '{resume[:100] if resume else 'None'}...'")
    return {'latest_user_message': resume}

# Determine if the user is finished creating their AI agent or not
async def route_user_message(state: AgentState):
    log_node("Router", "Determining conversation route...")
    log_state(f"User message: {state['latest_user_message'][:100]}...")
    
    prompt = f"""
    The user has sent a message: 
    
    {state['latest_user_message']}

    If the user wants to end the conversation, respond with just the text "finish_conversation".
    If the user wants to continue coding the AI agent, respond with just the text "coder_agent".
    """

    log_agent("Router", "Analyzing user intent...")
    result = await router_agent.run(prompt)
    next_action = result.data

    if next_action == "finish_conversation":
        log_success(f"🏁 Routing to: FINISH CONVERSATION")
        return "finish_conversation"
    else:
        log_success(f"🔄 Routing to: CODER AGENT (continue)")
        return "coder_agent"

# End of conversation agent to give instructions for executing the agent
async def finish_conversation(state: AgentState, writer):
    log_node("Finish Conversation", "Ending conversation and providing instructions")
    
    # Get the message history into the format for Pydantic AI
    message_history: list[ModelMessage] = []
    for message_row in state['messages']:
        message_history.extend(ModelMessagesTypeAdapter.validate_json(message_row))
    log_info(f"Loaded {len(message_history)} messages for final response")

    # Run the agent in a stream
    log_agent("End Conversation", "Generating farewell message and instructions...")
    if is_ollama:
        writer = get_stream_writer()
        result = await end_conversation_agent.run(state['latest_user_message'], message_history= message_history)
        writer(result.data)
        log_success("End conversation message generated (Ollama mode)")
    else: 
        async with end_conversation_agent.run_stream(
            state['latest_user_message'],
            message_history= message_history
        ) as result:
            # Stream partial text as it arrives
            async for chunk in result.stream_text(delta=True):
                writer(chunk)
        log_success("End conversation message streamed (OpenAI mode)")

    log_state("Conversation ended, updating final state")
    return {"messages": [result.new_messages_json()]}        

# Build workflow
log_step("🔨 Building LangGraph workflow...")
builder = StateGraph(AgentState)

# Add nodes
log_step("Adding nodes to graph...")
builder.add_node("define_scope_with_reasoner", define_scope_with_reasoner)
builder.add_node("coder_agent", coder_agent)
builder.add_node("get_next_user_message", get_next_user_message)
builder.add_node("finish_conversation", finish_conversation)
log_success("All nodes added")

# Set edges: define scope -> coder -> finish (straight-through)
log_step("Configuring edges...")
builder.add_edge(START, "define_scope_with_reasoner")
builder.add_edge("define_scope_with_reasoner", "coder_agent")
builder.add_edge("coder_agent", "finish_conversation")
builder.add_edge("finish_conversation", END)
log_success("Edges configured")

# Configure persistence
log_step("Setting up memory persistence...")
memory = MemorySaver()
agentic_flow = builder.compile(checkpointer=memory)
log_success("✨ Agentic workflow compiled and ready!")
log_step("=" * 60)