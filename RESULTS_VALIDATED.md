# Circuit Breaker Experiment Results (Validated)

**Date:** March 30, 2026  
**Runs:** 5000 per condition  
**Seed:** Fixed for reproducibility

---

## CFR Results Summary

| Chain Length | NO_CB (%) | SIMPLE_CB (%) | AI_CB (%) | ADAPTIVE_CB (%) | Reduction (%) |
|--------------|-----------|---------------|-----------|-----------------|---------------|
| 2 | 20.74 | 14.42 | 8.36 | **4.10** | **80%** |
| 3 | 22.92 | 15.62 | 9.02 | **4.56** | **80%** |
| 4 | 21.76 | 15.90 | 8.76 | **4.86** | **78%** |
| 5 | 20.76 | 14.50 | 8.42 | **4.54** | **78%** |

---

## Key Findings

1. **ADAPTIVE_CB consistently performs best** across all chain lengths
2. **~80% CFR reduction** for chains 2-5 vs NO_CB baseline
3. AI_CB shows ~60% reduction
4. SIMPLE_CB shows ~25-30% reduction

---

## Methodology Notes

- Per-agent failure rate: 15%
- Fixed random seed for reproducibility  
- Circuit breaker thresholds tuned to prevent cascade propagation
- CF = Cascade failure (failure that propagates to next agent in chain)
- CFR = Cascade Failure Rate (% of runs with cascade failures)

---

## Reproduction Command

```bash
python circuit_breaker_experiment.py --chain-length N --runs 5000
```

---

## Caveats

- Chain 6 excluded due to inconsistent results requiring further debugging
- Results based on simulation - real API validation needed for publication