# B. BASELINE SYSTEMS (COMPARATIVE EVALUATION)

Design controlled experiments comparing the proposed system against at least these baselines.

## 1. Single LLM (Gemini 3 Pro Preview)
*   **Description**: The Gemini 3 Pro model queried directly without tools, graph orchestration, or RAG.
*   **Purpose**: Establish a lower bound for performance and highlight the value of agency.
*   **Configuration**:
    *   System Prompt: "You are a helpful assistant."
    *   Tools: None.
    *   Retrieval: None (rely on parametric knowledge).
    *   Model: `gemini-exp-1206` (or current 3 Pro Preview version).

## 2. ReAct-style Agent
*   **Description**: A standard ReAct loop using LangChain or PydanticAI's basic agent, without the specific multi-agent graph structure or dedicated Refiner.
*   **Purpose**: Evaluate if the complex graph structure adds value over a simple reasoning loop.
*   **Configuration**:
    *   Tools: Same toolset as the full system.
    *   Architecture: Single agent loop (Think -> Act -> Observe).
    *   Prompt: "Solve the user's request using the available tools."

## 3. AutoGPT / BabyAGI-style Planner
*   **Description**: An agent that breaks the task into a todo list and executes it sequentially.
*   **Purpose**: Compare against explicit planning architectures.
*   **Configuration**:
    *   Phase 1: Generate plan.
    *   Phase 2: Execute steps sequentially.
    *   No dynamic graph routing (linear execution).

## 4. RAG-only LLM
*   **Description**: Retrieval-Augmented Generation without tool use or agentic loops.
*   **Purpose**: Isolate the impact of the Knowledge Base.
*   **Configuration**:
    *   Retrieval: Retrieve top-k chunks from Supabase based on user query.
    *   Context: Inject chunks into system prompt.
    *   Tools: None.
    *   Graph: None.

## Experimental Controls
All baselines must:
1.  **Use the same prompts** (where applicable, e.g., task description).
2.  **Use the same dataset** (the Benchmark tasks).
3.  **Use the same Gemini model** (`gemini-exp-1206`).
4.  **Be evaluated under identical conditions** (network environment, API quotas).
