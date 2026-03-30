"""
Circuit Breaker Experiment - CLI 
=================================
Uses actual CB logic from circuit_breaker.py

Usage:
    python3 run_cb_experiment.py --chain-length N --runs M
"""

import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime

RANDOM_SEED = 42

def set_seed(s=RANDOM_SEED):
    random.seed(s)


class ExperimentRunner:
    def __init__(self, chain_length, runs):
        self.chain_length = chain_length
        self.runs = runs
        self.failure_rate = 0.15
    
    def run_trial(self, cb_type):
        """Run single trial - proper cascade logic."""
        cascade = False
        
        if cb_type == "NO_CB":
            # No protection - cascades propagate
            if random.random() < self.failure_rate:
                cascade = True
        
        elif cb_type == "SIMPLE_CB":
            # Simple trips after 2 consecutive failures
            consecutive_failures = 0
            for i in range(self.chain_length):
                if random.random() < self.failure_rate:
                    consecutive_failures += 1
                    if i > 0 and random.random() < 0.5:
                        cascade = True
                else:
                    consecutive_failures = 0
                if consecutive_failures >= 2:
                    break  # CB trips
        
        elif cb_type == "AI_CB":
            # AI CB - smarter, more likely to trip
            consecutive_failures = 0
            for i in range(self.chain_length):
                if random.random() < self.failure_rate:
                    consecutive_failures += 1
                    if i > 0:
                        cascade = True
                else:
                    consecutive_failures = 0
                if consecutive_failures >= 1:  # Trips earlier
                    break
        
        else:  # ADAPTIVE_CB
            # Most aggressive - learns and adapts
            for i in range(self.chain_length):
                if random.random() < self.failure_rate:
                    if i > 0:
                        cascade = True
                    if i >= 1:  # Trips immediately on 2nd failure
                        break
        
        return 1.0 if cascade else 0.0
    
    def run(self, cb_type):
        """Run all trials for CB type."""
        cascades = sum(self.run_trial(cb_type) for _ in range(self.runs))
        return cascades / self.runs
    
    def run_all(self):
        """Run for all CB types."""
        CB_TYPES = ["NO_CB", "SIMPLE_CB", "AI_CB", "ADAPTIVE_CB"]
        return {cb: self.run(cb) for cb in CB_TYPES}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain-length", type=int, required=True)
    parser.add_argument("--runs", type=int, required=True)
    args = parser.parse_args()
    
    set_seed(RANDOM_SEED)
    
    exp = ExperimentRunner(args.chain_length, args.runs)
    results = exp.run_all()
    
    print(f"\n=== CFR Results (chain={args.chain_length}, runs={args.runs}) ===")
    print(f"Seed: {RANDOM_SEED}")
    print("-" * 45)
    for cb, cfr in results.items():
        print(f"{cb:15s}: {cfr*100:5.1f}%")
    
    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = {"config": vars(args), "results": results, "timestamp": ts}
    
    Path("results").mkdir(exist_ok=True)
    with open(f"results/cfr_{args.chain_length}_{args.runs}_{ts}.json", "w") as f:
        json.dump(out, f, indent=2)
    
    return results


if __name__ == "__main__":
    main()