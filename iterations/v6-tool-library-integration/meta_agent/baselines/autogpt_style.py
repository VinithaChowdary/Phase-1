from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel
# from pydantic_ai.models.vertexai import VertexAIModel
from dotenv import load_dotenv
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.utils import get_env_var

load_dotenv()

class LinearPlannerBaseline:
    def __init__(self):
        self.provider = get_env_var('LLM_PROVIDER') or 'OpenAI'
        self.base_url = get_env_var('BASE_URL') or 'https://api.openai.com/v1'
        self.api_key = get_env_var('LLM_API_KEY') or 'no-llm-api-key-provided'

        model_name = get_env_var('PRIMARY_MODEL') or 'gpt-4o-mini'
        
        if self.provider == "Anthropic":
            self.model = AnthropicModel(model_name, api_key=self.api_key)
        elif self.provider == "Gemini":
            # self.model = VertexAIModel(model_name)
            raise NotImplementedError("VertexAI not installed")
        else:
            self.model = OpenAIModel(model_name, base_url=self.base_url, api_key=self.api_key)

        self.planner_agent = Agent(
            self.model,
            system_prompt="You are a planning agent. Break down the user's request into a sequential list of steps to build a python AI agent."
        )
        
        self.executor_agent = Agent(
            self.model,
            system_prompt="You are an execution agent. Given a plan, write the full python code for the requested AI agent. Do not ask clarifying questions, just write the best code you can."
        )

    async def run(self, task_prompt: str) -> str:
        # Phase 1: Plan
        plan_result = await self.planner_agent.run(task_prompt)
        plan = plan_result.data
        
        # Phase 2: Execute
        execution_prompt = f"""
        User Request: {task_prompt}
        
        Implementation Plan:
        {plan}
        
        Please generate the complete Python code for this agent following the plan.
        """
        
        result = await self.executor_agent.run(execution_prompt)
        return result.data
