"""
Run Experiment v3 - FIXED STOCHASTIC
Date: 2026-03-30 12:00
Status: FIXING - cascade detection needs rewrite
"""

import argparse
import random

def run_trial(chain_length, cb_type):
    """Fixed: returns 1 if cascade happened, 0 otherwise."""
    fail_count = 0
    
    for i in range(chain_length):
        is_failure = random.random() < 0.15
        
        if is_failure:
            fail_count += 1
            
            # CB logic: does it block before cascade?
            if cb_type == "NO_CB":
                # no blocking - any failure cascades  
                if fail_count > 0:
                    return 1  # cascade!
            elif cb_type == "SIMPLE_CB":
                if fail_count >= 2:
                    return 0  # blocked by CB, no cascade
                # otherwise continue
            elif cb_type in ("AI_CB", "ADAPTIVE_CB"):
                if fail_count >= 1:
                    return 0  # blocked, more aggressive
            # else continue chain
        else:
            fail_count = 0  # reset on success
    
    return 0  # no cascade occurred

def main():
    import sys
    chain = int(sys.argv[1])
    runs = int(sys.argv[2])
    
    for cb in ["NO_CB", "SIMPLE_CB", "AI_CB", "ADAPTIVE_CB"]:
        random.seed(42)
        c = sum(run_trial(chain, cb) for _ in range(runs)) / runs
        print(f"{cb}: {c*100:.1f}%")

if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]), int(sys.argv[2]))