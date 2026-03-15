# A. NUMERICAL METRICS DESIGN

## 1. Agent Performance Metrics

### Task Success Rate (TSR)
*   **Definition**: The percentage of tasks where the agent produces a correct and complete solution without human intervention.
*   **Formula**: $TSR = \frac{\text{Count(Success)}}{\text{Total Tasks}} \times 100\%$
*   **Measurement**: Automated verification script checks if the output satisfies the acceptance criteria (e.g., code runs, passes unit tests, file exists).
*   **Logging**: Log binary success/failure status per `task_id`.

### Tool Invocation Accuracy (TIA)
*   **Definition**: The ratio of correct tool selections to total tool invocations.
*   **Formula**: $TIA = \frac{\sum_{i=1}^{N} \mathbb{1}(Tool_i = GroundTruth_i)}{N}$
*   **Measurement**: Compare the sequence of invoked tools against a "golden path" trace for benchmark tasks.
*   **Logging**: Log `(step_id, tool_name, arguments)` for every tool call.

### Schema Validity Rate (SVR)
*   **Definition**: The percentage of agent outputs (tool arguments, final responses) that strictly adhere to the defined Pydantic schemas or JSON specs.
*   **Formula**: $SVR = \frac{\text{Count(Valid Schemas)}}{\text{Total Output Events}} \times 100\%$
*   **Measurement**: Catch JSON parsing errors and Pydantic validation exceptions.
*   **Logging**: Log `validation_error` events.

### Hallucination Rate (HR)
*   **Definition**: The percentage of tool calls referencing non-existent resources (files, API endpoints) or fabricating parameters.
*   **Formula**: $HR = \frac{\text{Count(Invalid Resource Calls)}}{\text{Total Tool Calls}} \times 100\%$
*   **Measurement**: Check if file paths exist before read/write; verify API endpoints against OpenAPI specs.
*   **Logging**: Log `FileNotFoundError` or 404/500 API responses triggered by agent arguments.

## 2. Reasoning & Workflow Metrics

### Mean Graph Traversal Depth (MGTD)
*   **Definition**: The average number of nodes visited in the LangGraph execution path per task.
*   **Formula**: $MGTD = \frac{1}{M} \sum_{j=1}^{M} \text{NodesVisited}_j$
*   **Measurement**: Count transitions in the LangGraph state history.
*   **Logging**: Log `node_entry` events with timestamps.

### Average Nodes Executed per Task
*   **Definition**: Similar to depth, but counts total node executions (including loops).
*   **Measurement**: Count total entries in `state['messages']` or internal graph steps.

### Refinement Iterations until Convergence
*   **Definition**: The number of times the `Refiner` agent rejects a solution and requests changes before final acceptance.
*   **Measurement**: Count cycles where `router_agent` returns `refine` or `coder_agent` loops back.
*   **Logging**: Log `refinement_triggered` events.

### Failure Recovery Rate (FRR)
*   **Definition**: The percentage of tasks where the agent encounters a runtime error (e.g., tool failure) but successfully completes the task subsequently.
*   **Formula**: $FRR = \frac{\text{Count(Error \land Success)}}{\text{Count(Error)}} \times 100\%$
*   **Measurement**: Identify tasks with logged errors that eventually end in `Success` state.

## 3. Efficiency Metrics

### End-to-End Latency
*   **Definition**: Wall-clock time from initial prompt to final answer.
*   **Metrics**: Mean, P95 (95th percentile).
*   **Logging**: `Timestamp(End) - Timestamp(Start)`.

### Token Usage per Task
*   **Definition**: Total input + output tokens consumed across all agent steps.
*   **Measurement**: Sum `usage.total_tokens` from LLM response metadata.
*   **Logging**: Log token counts per LLM call.

### Cost per Successful Task
*   **Definition**: Total inference cost averaged over successful tasks.
*   **Formula**: $\frac{\sum \text{Cost}}{\text{Count(Success)}}$
*   **Measurement**: Calculate based on token counts and Gemini 3 Pro pricing.

### Throughput under Concurrency
*   **Definition**: Number of tasks completed per minute when running $K$ concurrent sessions.
*   **Measurement**: Run load test with $K=10, 20, 50$.
