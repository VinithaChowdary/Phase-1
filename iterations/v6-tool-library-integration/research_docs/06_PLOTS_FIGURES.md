# F. PLOTS & FIGURES (REQUIRED)

All plots must be generated via `matplotlib` or `seaborn` from the structured logs.

## Figure 1: Success Rate vs System Variant
*   **Type**: Bar Chart (Vertical).
*   **X-Axis**: System Variants (Full, –Graph, –RAG, –MCP, –Refiner, Single LLM).
*   **Y-Axis**: Task Success Rate (%).
*   **Error Bars**: 95% Confidence Intervals.
*   **Insight**: Demonstrates the additive value of each component.

## Figure 2: Hallucination Rate vs Baseline
*   **Type**: Grouped Bar Chart.
*   **Groups**: Full System vs. ReAct vs. Single LLM.
*   **Y-Axis**: Hallucination Rate (%).
*   **Insight**: Proves that the graph/RAG architecture constrains model behavior effectively.

## Figure 3: Latency vs Graph Depth
*   **Type**: Scatter Plot with Regression Line.
*   **X-Axis**: Mean Graph Traversal Depth.
*   **Y-Axis**: End-to-End Latency (s).
*   **Color**: Task Difficulty Tier.
*   **Insight**: Shows the trade-off between reasoning depth and speed.

## Figure 4: Cost Efficiency
*   **Type**: Dual-Axis Line Chart.
*   **X-Axis**: Task Complexity (Tier 1 -> Tier 3).
*   **Y1-Axis (Left)**: Success Rate.
*   **Y2-Axis (Right)**: Cost per Successful Task ($).
*   **Insight**: Highlights where the system becomes cost-effective compared to brute-force LLM prompting.

## Figure 5: Ablation Impact Heatmap
*   **Type**: Heatmap.
*   **Rows**: System Variants.
*   **Columns**: Metrics (TSR, TIA, SVR, Latency, Cost).
*   **Color**: % Change relative to Full System (Green = Better, Red = Worse).
*   **Insight**: Dense summary of all ablation studies.
