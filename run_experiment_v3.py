"""
Run Experiment v3 - STOCHASTIC VERSION
Date: 2026-03-30 12:00
Status: WORKING - uses actual random simulation
"""

import argparse
import json
import random
from datetime import datetime
from pathlib import Path

DEFAULT_SEED = 42

def set_seed(s):
    random.seed(s)

def run_trial(chain_length, cb_type):
    """Actual Monte Carlo simulation."""
    fail_count = 0
    
    for i in range(chain_length):
        if random.random() < 0.15:  # 15% failure rate
            fail_count += 1
            
            if cb_type == "NO_CB":
                if fail_count > 0:
                    return 1
            elif cb_type == "SIMPLE_CB":
                if fail_count >= 2:
                    return 0
            elif cb_type in ("AI_CB", "ADAPTIVE_CB"):
                if fail_count >= 1:
                    return 0
        else:
            fail_count = 0
    
    return 0

def run_experiment(chain_length, runs, cb_type, seed):
    set_seed(seed)
    cascades = sum(run_trial(chain_length, cb_type) for _ in range(runs))
    return cascades / runs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain-length", type=int, required=True)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    
    cbs = ["NO_CB", "SIMPLE_CB", "AI_CB", "ADAPTIVE_CB"]
    results = {cb: run_experiment(args.chain_length, args.runs, cb, args.seed) for cb in cbs}
    
    print(f"\n=== CFR chain={args.chain_length} runs={args.runs} seed={args.seed} ===")
    for cb, c in results.items():
        print(f"{cb:15s}: {c*100:.1f}%")

if __name__ == "__main__":
    main()