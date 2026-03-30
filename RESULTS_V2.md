# Circuit Breaker Experiment Results v2

**Date:** 2026-03-30  
**Script:** run_experiment.py (v2)
**Runs:** 5000 per condition  
**Seed:** 42

## CFR Results

| Chain | NO_CB | SIMPLE_CB | AI_CB | ADAPTIVE_CB | Reduction |
|-------|-------|-----------|------|-----------|-----------|
| 2 | 13.7% | 9.0% | 5.3% | **2.8%** | **80%** |
| 3 | 20.7% | 13.8% | 7.9% | **4.4%** | **79%** |
| 4 | 26.5% | 18.7% | 10.5% | **5.8%** | **78%** |
| 5 | 33.3% | 23.0% | 12.8% | **7.3%** | **78%** |

## Key Findings

- ADAPTIVE_CB achieves ~78-80% CFR reduction across all chains
- Higher chain length = higher baseline CFR (as expected)
- AI_CB shows ~60% reduction
- SIMPLE_CB shows ~25-30% reduction

## Reproduce

```bash
python3 run_experiment.py --chain-length N --runs M
```