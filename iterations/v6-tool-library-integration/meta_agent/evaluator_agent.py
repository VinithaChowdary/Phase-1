from __future__ import annotations as _annotations

import logfire
from pydantic import BaseModel, Field
from typing import List, Literal
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel
# from pydantic_ai.models.vertexai import VertexAIModel
from dotenv import load_dotenv

from utils.utils import get_env_var
from meta_agent.agent_prompts import evaluator_prompt

load_dotenv()

# Configure logfire
logfire.configure(send_to_logfire='if-token-present')

# Define the structured output for evaluation
class ConfidenceScore(BaseModel):
    score: float = Field(description="Confidence score between 0.0 and 1.0, where 1.0 is perfect confidence.")
    reasoning: str = Field(description="Detailed explanation of why this score was given, highlighting issues or strengths.")
    needs_refinement: bool = Field(description="True if the code needs significant improvement before showing to the user.")
    refinement_targets: List[Literal["prompt", "tools", "agent"]] = Field(
        default_factory=list, 
        description="List of components that specifically need refinement (e.g. ['prompt'] if instructions are unclear, ['tools'] if tools are missing)."
    )

provider = get_env_var('LLM_PROVIDER') or 'OpenAI'
base_url = get_env_var('BASE_URL') or 'https://api.openai.com/v1'
api_key = get_env_var('LLM_API_KEY') or 'no-llm-api-key-provided'

# Use a strong model for evaluation (Reasoner or Primary)
# Using the same logic as reasoner (o3-mini or similar high capability model)
reasoner_model_name = get_env_var('REASONER_MODEL') or 'o3-mini'

if provider == "Anthropic":
    model = AnthropicModel(reasoner_model_name, api_key=api_key)
elif provider == "Gemini":
    # model = VertexAIModel(reasoner_model_name)
    raise NotImplementedError("VertexAI not installed")
else:
    model = OpenAIModel(reasoner_model_name, base_url=base_url, api_key=api_key)

evaluator_agent = Agent(
    model,
    result_type=ConfidenceScore,
    system_prompt=evaluator_prompt
)
