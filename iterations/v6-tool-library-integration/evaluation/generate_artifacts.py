import json
import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np
from datetime import datetime

def load_logs(log_file):
    data = []
    with open(log_file, 'r') as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return pd.DataFrame(data)

def generate_plots(df, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    if df.empty:
        print("No data to plot.")
        return

    # Pre-processing: Convert status to boolean for easier mean calc
    df['success'] = df['status'] == 'success'
    df['success_int'] = df['success'].astype(int) * 100
    
    # Figure 1: Overall Success Rate by Variant (with CI)
    plt.figure(figsize=(10, 6))
    if 'variant' in df.columns:
        sns.barplot(x='variant', y='success_int', data=df, errorbar=('ci', 95), capsize=.1)
        plt.title('Success Rate by System Variant (95% CI)')
        plt.ylabel('Success Rate (%)')
        plt.savefig(os.path.join(output_dir, 'success_rate_by_variant.png'))
        plt.close()
    
    # Figure 2: Latency Distribution by Variant
    plt.figure(figsize=(10, 6))
    if 'latency_ms' in df.columns:
        sns.boxplot(x='variant', y='latency_ms', data=df)
        plt.title('Latency Distribution by Variant')
        plt.ylabel('Latency (ms)')
        plt.savefig(os.path.join(output_dir, 'latency_by_variant.png'))
        plt.close()

    # Figure 3: Success Rate by Complexity
    plt.figure(figsize=(12, 6))
    if 'complexity' in df.columns:
        sns.barplot(x='variant', y='success_int', hue='complexity', data=df, errorbar=('ci', 95), capsize=.1)
        plt.title('Success Rate by Task Complexity and Variant')
        plt.ylabel('Success Rate (%)')
        plt.legend(title='Task Complexity')
        plt.savefig(os.path.join(output_dir, 'success_rate_by_complexity.png'))
        plt.close()

    # Figure 4: Confidence Score Analysis (New)
    plt.figure(figsize=(10, 6))
    if 'confidence_score' in df.columns and df['confidence_score'].notna().any():
        # Boxplot of Confidence by Status
        sns.boxplot(x='status', y='confidence_score', data=df, hue='variant')
        plt.title('Confidence Score Distribution by Outcome')
        plt.ylabel('Confidence Score (0-1)')
        plt.savefig(os.path.join(output_dir, 'confidence_by_outcome.png'))
        plt.close()

    # Figure 5: Refinement Impact (New)
    plt.figure(figsize=(10, 6))
    if 'refinement_count' in df.columns:
        # Filter for Full System only where refinement is applicable
        fs_df = df[df['variant'] == 'full_system']
        if not fs_df.empty:
            sns.barplot(x='refinement_count', y='success_int', data=fs_df, errorbar=('ci', 95), capsize=.1)
            plt.title('Success Rate by Refinement Count (Full System)')
            plt.ylabel('Success Rate (%)')
            plt.xlabel('Number of Refinements Triggered')
            plt.savefig(os.path.join(output_dir, 'success_by_refinement.png'))
            plt.close()

def generate_trace_artifact(df, output_dir):
    if 'message_history' not in df.columns:
        return

    # Find a successful Full System run with refinement if possible
    valid_history = df['message_history'].apply(lambda x: isinstance(x, list) and len(x) > 0)
    
    # Prioritize runs with refinement > 0
    refined_runs = df[(df['variant'] == 'full_system') & (df['status'] == 'success') & valid_history & (df.get('refinement_count', 0) > 0)]
    
    if not refined_runs.empty:
        run = refined_runs.iloc[0]
    else:
        # Fallback to any successful run
        trace_run = df[(df['variant'] == 'full_system') & (df['status'] == 'success') & valid_history]
        if trace_run.empty:
            return
        run = trace_run.iloc[0]

    history = run['message_history'] 
    
    trace_path = os.path.join(output_dir, 'TRACE_EXAMPLE.md')
    
    with open(trace_path, 'w') as f:
        f.write(f"# Qualitative Execution Trace\n")
        f.write(f"**Task ID**: {run['task_id']}\n")
        f.write(f"**Variant**: {run['variant']}\n")
        f.write(f"**Complexity**: {run['complexity']}\n")
        f.write(f"**Refinement Count**: {run.get('refinement_count', 0)}\n")
        f.write(f"**Final Confidence**: {run.get('confidence_score', 'N/A')}\n\n")
        
        f.write("## Execution Log\n\n")
        for i, msg in enumerate(history):
            f.write(f"### Step {i+1}\n")
            try:
                f.write(f"```\n{msg}\n```\n\n")
            except:
                pass

def generate_report(df, output_dir):
    report_path = os.path.join(output_dir, 'EXPERIMENTAL_REPORT.md')
    
    if df.empty:
        return

    total_tasks = len(df)
    success_rate = (df['status'] == 'success').mean() * 100 if total_tasks > 0 else 0
    
    report_content = f"""# Experimental Report

## Summary
*   **Total Runs**: {total_tasks}
*   **Overall Success Rate**: {success_rate:.2f}%

## Performance by Variant (Mean ± Std)

| Variant | Success Rate (%) | Avg Latency (ms) | Avg Confidence | Avg Refinements | Runs |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    if 'variant' in df.columns:
        variants = df['variant'].unique()
        for v in variants:
            v_df = df[df['variant'] == v]
            v_success_mean = (v_df['status'] == 'success').mean() * 100
            v_success_std = (v_df['status'] == 'success').std() * 100
            v_latency_mean = v_df['latency_ms'].mean()
            v_count = len(v_df)
            
            v_conf = v_df['confidence_score'].mean() if 'confidence_score' in v_df.columns else 0
            v_ref = v_df['refinement_count'].mean() if 'refinement_count' in v_df.columns else 0
            
            report_content += f"| {v} | {v_success_mean:.1f} ± {v_success_std:.1f}% | {v_latency_mean:.0f} | {v_conf:.2f} | {v_ref:.1f} | {v_count} |\n"

    report_content += "\n## Adaptive Graph Metrics\n"
    if 'refinement_count' in df.columns:
        ref_dist = df[df['variant']=='full_system']['refinement_count'].value_counts().sort_index()
        report_content += "\n### Refinement Distribution (Full System)\n"
        report_content += ref_dist.to_markdown() if hasattr(ref_dist, 'to_markdown') else str(ref_dist)
        report_content += "\n"

    # Add Complexity Split Table
    report_content += "\n## Success by Task Complexity\n\n"
    if 'complexity' in df.columns and 'variant' in df.columns:
        try:
            pivot = df.groupby(['variant', 'complexity'])['success_int'].mean().unstack().round(1)
            report_content += pivot.to_string()
        except Exception:
            pass
        report_content += "\n"

    with open(report_path, 'w') as f:
        f.write(report_content)

def main():
    log_file = "journal_artifacts/logs/experiment_data.jsonl"
    output_dir = "journal_artifacts"
    figures_dir = os.path.join(output_dir, "figures")
    
    if not os.path.exists(log_file):
        print(f"Log file {log_file} not found.")
        return
        
    df = load_logs(log_file)
    generate_plots(df, figures_dir)
    generate_trace_artifact(df, output_dir)
    generate_report(df, output_dir)
    
    print("Artifacts generated.")

if __name__ == "__main__":
    main()
