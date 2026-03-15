# D. DATASET & TASK BENCHMARKS

Define reproducible evaluation tasks (N=50) across 3 difficulty tiers.

## Tier 1: Documentation-Based Agent Generation (20 Tasks)
*   **Description**: Create agents that simply wrap a documentation page or a simple API.
*   **Example**: "Create an agent that can answer questions about Pydantic V2 models."
*   **Ground Truth**: Agent must import `pydantic`, define a model, and have a system prompt referencing the docs.
*   **Constraint**: Must use RAG to find the correct syntax.

## Tier 2: Multi-Step Tool Orchestration (20 Tasks)
*   **Description**: Create agents that use 2+ tools to solve a problem.
*   **Example**: "Create a GitHub agent that can search for a repo, list its files, and read the README."
*   **Ground Truth**: Agent tool definitions match the `github` MCP schema. Correct dependency injection.
*   **Constraint**: Must handle tool outputs correctly (e.g., parsing JSON).

## Tier 3: Ambiguous / Noisy Queries (10 Tasks)
*   **Description**: Requests with missing information or conflicting requirements.
*   **Example**: "Make me a bot that does stuff with data."
*   **Ground Truth**: Agent must ask clarifying questions (Refiner loop) before generating code.
*   **Constraint**: Success is defined by *not* hallucinating a solution immediately.

## Task Specification Format
For each task, provide:
1.  **Prompt Template**: The exact string fed to the `latest_user_message`.
2.  **Success Criteria**: A Python assertion script (e.g., `assert 'import pydantic' in code`).
3.  **Timeout**: Max seconds allowed.
4.  **Max Steps**: Max graph transitions.

## Partial Tool Failure Scenarios
In 10% of runs, simulate:
*   **API Timeout**: Tool call hangs.
*   **500 Error**: Tool returns internal server error.
*   **Malformed JSON**: Tool returns invalid JSON.

**Metric**: `Failure Recovery Rate` is critical here.
