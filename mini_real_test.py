#!/usr/bin/env python3
"""
Mini real API test - 2 runs per condition to verify full experiment flow.
"""
import sys
from pathlib import Path

# Add current directory to path
HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))

def run_mini_real_test():
    """Run a minimal real API test."""
    print("🧪 Running mini real API test (2 runs per condition)...")
    
    from experiment_runner import ExperimentRunner
    
    # Run with only 2 runs per condition for speed
    runner = ExperimentRunner(runs_per_condition=2, pilot=True, real_mode=True)
    
    # Just run one condition for now to test
    print("Testing AI_CB condition...")
    results = runner.run_condition("AI_CB")
    
    print(f"\n✅ Results: {len(results)} runs completed")
    for i, result in enumerate(results):
        print(f"  Run {i+1}: completed={result['task_completed']}, CFR={result['cfr']['cfr_rate']:.4f}")
    
    return results

if __name__ == "__main__":
    run_mini_real_test()