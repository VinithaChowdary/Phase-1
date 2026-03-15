# C. ABLATION STUDIES (CRITICAL)

Design ablation experiments to quantify the contribution of each system component.

## 1. –Graph (Sequential Execution)
*   **Modification**: Remove the conditional edges in LangGraph. Force a linear path: `Scope -> Advisor -> Coder -> Finish`.
*   **Hypothesis**: Lower success rate on complex tasks requiring iteration; faster latency on simple tasks.
*   **Implementation**: Create a `meta_agent_linear.py` that removes `router_agent` and `get_next_user_message` loops.

## 2. –RAG (No Document Grounding)
*   **Modification**: Disable `advisor_with_examples` and `define_scope_with_reasoner`'s access to `list_documentation_pages_tool`.
*   **Hypothesis**: Higher hallucination rate; lower code quality for specific libraries (PydanticAI).
*   **Implementation**: Pass empty list to `documentation_pages` and `file_list`.

## 3. –MCP (Hardcoded Tool Calls)
*   **Modification**: Replace dynamic MCP tool discovery with a fixed set of hardcoded tools.
*   **Hypothesis**: Reduced adaptability to new environments; comparable performance on known tasks.
*   **Implementation**: Modify `AdvisorDeps` to ignore `agent-resources/mcps`.

## 4. –Refiner (No Feedback Loop)
*   **Modification**: Bypass the `refine_prompt`, `refine_tools`, and `refine_agent` nodes. The user's feedback goes directly back to `coder_agent` without an intermediate refinement step.
*   **Hypothesis**: More iterations required to converge; lower final code quality.
*   **Implementation**: Change edge from `route_user_message` to always point to `coder_agent` (or remove router logic).

## 5. –Memory (Stateless Execution)
*   **Modification**: Disable `MemorySaver` checkpointer in LangGraph. Treat every turn as a fresh start (or limited context window).
*   **Hypothesis**: Complete failure on multi-turn tasks.
*   **Implementation**: `builder.compile(checkpointer=None)`.

## Comparison Table

| Variant | TSR | TIA | HR | Latency | Cost |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Full System** | **--** | **--** | **--** | **--** | **--** |
| –Graph | -- | -- | -- | -- | -- |
| –RAG | -- | -- | -- | -- | -- |
| –MCP | -- | -- | -- | -- | -- |
| –Refiner | -- | -- | -- | -- | -- |
| –Memory | -- | -- | -- | -- | -- |
