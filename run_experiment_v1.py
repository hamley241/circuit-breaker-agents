"""
Run Experiment v1 - FIRST VERSION (Broken)
Date: 2026-03-30 05:00
Status: BROKEN - gave inconsistent results
Smoke test: FAILED
"""

import argparse
import json
import random
from datetime import datetime
from pathlib import Path

# Original broken logic - multiple issues
RANDOM_SEED = 42
FAILURE_RATE = 0.15

def set_seed(s=RANDOM_SEED):
    random.seed(s)

def run_trial(chain_length, cb_type):
    raise Exception("V1 broken - do not use")

def main():
    raise Exception("V1 broken - do not use")

if __name__ == "__main__":
    raise Exception("V1 broken - use v2")