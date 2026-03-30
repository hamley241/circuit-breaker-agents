#!/usr/bin/env python3
"""
Cost estimator for exp-001 real API experiments.
"""
import sys
from pathlib import Path

# Add current directory to path
HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))

def main():
    """Show cost estimates for different experiment configurations."""
    from api_clients import CostEstimator
    
    print("💰 exp-001 Real API Cost Estimates")
    print("=" * 50)
    
    configs = [
        {"name": "Pilot (10 runs/condition)", "runs": 10, "conditions": 5},
        {"name": "Full (55 runs/condition)", "runs": 55, "conditions": 5},
        {"name": "Minimal (5 runs/condition)", "runs": 5, "conditions": 5},
    ]
    
    for config in configs:
        print(f"\n📊 {config['name']}")
        print("-" * 30)
        
        cost = CostEstimator.estimate_experiment_cost(
            runs_per_condition=config['runs'],
            num_conditions=config['conditions']
        )
        
        print(f"  Total API calls: {cost['total_calls']}")
        print(f"  OpenAI cost:     ${cost['openai_cost']:.2f}")
        print(f"  Claude cost:     ${cost['claude_cost']:.2f}")
        print(f"  Total cost:      ${cost['total_cost']:.2f}")
        print(f"  Cost per call:   ${cost['cost_per_call']:.4f}")
    
    print("\n📝 Notes:")
    print("  - Estimates based on ~150 input + ~300 output tokens per call")
    print("  - Assumes mixed GPT-4o/Claude-3-Sonnet usage")
    print("  - Actual costs may vary based on prompt complexity")
    print("  - If only OpenAI available, multiply OpenAI cost by 2")

if __name__ == "__main__":
    main()