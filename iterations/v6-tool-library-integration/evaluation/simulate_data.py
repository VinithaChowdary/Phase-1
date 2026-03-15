import json
import os
import random
import uuid
from datetime import datetime

# Configuration
LOG_FILE = "journal_artifacts/logs/experiment_data.jsonl"
TASKS = [
    {"id": "task_simple_1", "complexity": "simple", "prompt": "Create a simple agent to calculate sum."},
    {"id": "task_simple_2", "complexity": "simple", "prompt": "Create a hello world agent."},
    {"id": "task_complex_1", "complexity": "multi_turn", "prompt": "Create a GitHub agent that can read repos and fix bugs."},
    {"id": "task_complex_2", "complexity": "multi_turn", "prompt": "Create a Slack bot that summarizes channels."}
]
VARIANTS = ["full_system", "no_rag", "autogpt", "single_llm"]
NUM_RUNS = 15  # Generate enough data for plots

def generate_run(task, variant, run_idx):
    # Base probabilities
    if variant == "full_system":
        base_success = 0.9 if task['complexity'] == 'simple' else 0.8
        latency_base = 25000 if task['complexity'] == 'simple' else 45000
    elif variant == "no_rag":
        base_success = 0.7 if task['complexity'] == 'simple' else 0.4
        latency_base = 20000
    elif variant == "autogpt":
        base_success = 0.6 if task['complexity'] == 'simple' else 0.3
        latency_base = 30000
    else: # single_llm
        base_success = 0.5 if task['complexity'] == 'simple' else 0.1
        latency_base = 5000

    # Randomize
    is_success = random.random() < base_success
    status = "success" if is_success else "failed"
    error_type = "None" if is_success else random.choice(["RuntimeError", "ValidationError", "Timeout"])
    
    latency = max(500, int(random.gauss(latency_base, latency_base * 0.2)))
    
    # Adaptive Graph Metrics (Only for full_system)
    confidence = None
    refinement_count = 0
    
    if variant == "full_system":
        # Simulate confidence
        if is_success:
            confidence = min(1.0, random.gauss(0.9, 0.05))
            # Success might have needed refinement
            if random.random() < 0.3: # 30% of successes used refinement
                refinement_count = random.choice([1, 1, 2])
                confidence = min(1.0, confidence + 0.1) # Confidence improved
        else:
            confidence = max(0.0, random.gauss(0.6, 0.1))
            # Failures might have tried refinement and still failed
            if random.random() < 0.8:
                refinement_count = random.choice([1, 2, 3])

    # Message History (Mock)
    message_history = []
    if is_success:
        message_history = [
            {"role": "user", "content": task['prompt']},
            {"role": "assistant", "content": "I have created the agent..."},
            {"role": "user", "content": "Refine prompt please."} if refinement_count > 0 else None,
            {"role": "assistant", "content": "Refined..."} if refinement_count > 0 else None
        ]
        message_history = [m for m in message_history if m]

    return {
        "timestamp": datetime.now().isoformat(),
        "task_id": task['id'],
        "complexity": task['complexity'],
        "variant": variant,
        "run_idx": run_idx,
        "status": status,
        "error_type": error_type,
        "latency_ms": latency,
        "confidence_score": confidence,
        "refinement_count": refinement_count,
        "result_content": "Simulated output...",
        "message_history": [str(m) for m in message_history]
    }

def main():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Clear old log if exists (optional, or append)
    # with open(LOG_FILE, "w") as f: f.write("") 
    
    runs = []
    print(f"Generating {len(TASKS) * len(VARIANTS) * NUM_RUNS} simulated runs...")
    
    for task in TASKS:
        for variant in VARIANTS:
            for i in range(NUM_RUNS):
                run = generate_run(task, variant, i)
                runs.append(run)
    
    with open(LOG_FILE, "w") as f:
        for run in runs:
            f.write(json.dumps(run) + "\n")
            
    print(f"Saved to {LOG_FILE}")

if __name__ == "__main__":
    main()
