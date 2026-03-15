# Experimental Report

## Summary
*   **Total Runs**: 240
*   **Overall Success Rate**: 59.58%

## Performance by Variant (Mean ± Std)

| Variant | Success Rate (%) | Avg Latency (ms) | Avg Confidence | Avg Refinements | Runs |
| :--- | :--- | :--- | :--- | :--- | :--- |
| full_system | 91.7 ± 27.9% | 35133 | 0.90 | 0.5 | 60 |
| no_rag | 56.7 ± 50.0% | 20116 | nan | 0.0 | 60 |
| autogpt | 48.3 ± 50.4% | 29449 | nan | 0.0 | 60 |
| single_llm | 41.7 ± 49.7% | 4990 | nan | 0.0 | 60 |

## Adaptive Graph Metrics

### Refinement Distribution (Full System)
|   refinement_count |   count |
|-------------------:|--------:|
|                  0 |      39 |
|                  1 |      11 |
|                  2 |       9 |
|                  3 |       1 |

## Success by Task Complexity

complexity   multi_turn  simple
variant                        
autogpt            36.7    60.0
full_system        86.7    96.7
no_rag             36.7    76.7
single_llm         20.0    63.3
