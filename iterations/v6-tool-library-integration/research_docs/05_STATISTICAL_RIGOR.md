# E. STATISTICAL RIGOR

## Sample Size
*   **Minimum Runs**: ≥30 runs per configuration per task tier.
*   **Total Data Points**: 5 configurations * 50 tasks * 30 runs = 7,500 traces.
*   **Justification**: Central Limit Theorem applies; sufficient power to detect 5% effect size difference.

## Reporting Standards
For every reported metric in the final paper:
1.  **Mean**: $\mu = \frac{1}{N}\sum x_i$
2.  **Standard Deviation**: $\sigma = \sqrt{\frac{1}{N-1}\sum(x_i - \mu)^2}$
3.  **Confidence Intervals**: 95% CI computed via bootstrapping (10,000 resamples).

## Significance Testing
*   **Success Rates (Binary)**: Fisher's Exact Test or Chi-Squared Test.
*   **Latency/Tokens (Continuous)**: Mann-Whitney U Test (non-parametric, as latency is often not normal).
*   **Correction**: Bonferroni correction for multiple hypothesis testing.

## Randomness Control
*   **Temperature**: Fixed at `0.0` for reproducibility where possible, or recorded if `0.7` is needed for creativity.
*   **Seeds**: Set `random_seed` for any Python logic.
*   **Gemini Determinism**: Use `generation_config={"temperature": 0.0}`.
