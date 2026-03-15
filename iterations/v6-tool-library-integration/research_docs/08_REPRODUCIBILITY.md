# H. REPRODUCIBILITY & APPENDIX MATERIAL

## Appendix A: Prompt Templates
Include the full text of:
1.  `advisor_agent` system prompt.
2.  `pydantic_ai_coder` system prompt.
3.  `refiner` instructions.

## Appendix B: Tool Schemas
List the JSON schemas for all MCP tools used in the evaluation:
*   GitHub (List, Read, Search).
*   Supabase (Search Docs).

## Appendix C: Evaluation Scripts
Pseudocode for the master evaluation loop:
```python
for variant in ["Full", "NoGraph", "NoRAG", "NoRefiner"]:
    for task in benchmark_tasks:
        for run in range(30):
            reset_environment()
            metrics = run_agent(variant, task)
            log_results(metrics)
```

## Logging Format
Standardize logs to JSONL:
```json
{
  "timestamp": "ISO8601",
  "task_id": "tier1_01",
  "variant": "full_system",
  "step": 3,
  "node": "coder_agent",
  "tool_calls": [...],
  "latency_ms": 1200,
  "tokens_in": 500,
  "tokens_out": 200,
  "status": "success"
}
```

## Random Seed Handling
*   Python `random.seed(42)`
*   Numpy `np.random.seed(42)`
*   Gemini `temperature=0.0`
