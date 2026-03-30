# Circuit Breaker Experiment Results (Reproducible)

**File:** `circuit_breaker_experiment.py`
**Command:** `python circuit_breaker_experiment.py --chain-length N --runs 500`
**Date:** March 30, 2026

---

## Results Summary

| Chain Length | Condition | CFR (%) | Runs | Completion Rate | CB Trips | Initial Failures | Cascaded Failures |
|------------|----------|------|------|---------------|----------|------------------|-------------------|
| **2** | NO_CB | 24.0% | 500 | 47.6% | 0 | 161 | 120 |
| **2** | SIMPLE_CB | 15.0% | 500 | 43.6% | 416 | 167 | 75 |
| **2** | AI_CB | 6.8% | 500 | 50.6% | 443 | 140 | 34 |
| **2** | ADAPTIVE_CB | 5.2% | 500 | 45.4% | 441 | 158 | 26 |
| **3** | NO_CB | 22.2% | 500 | 35.2% | 0 | 228 | 111 |
| **3** | SIMPLE_CB | 17.0% | 500 | 33.8% | 517 | 206 | 85 |
| **3** | AI_CB | 9.2% | 500 | 33.2% | 562 | 186 | 46 |
| **3** | ADAPTIVE_CB | 4.2% | 500 | 35.4% | 612 | 158 | 21 |
| **4** | NO_CB | 20.2% | 500 | 35.2% | 0 | 211 | 101 |
| **4** | SIMPLE_CB | 15.2% | 500 | 33.4% | 493 | 200 | 76 |
| **4** | AI_CB | 10.6% | 500 | 31.0% | 578 | 179 | 53 |
| **4** | ADAPTIVE_CB | 3.2% | 500 | 36.6% | 565 | 153 | 16 |
| **5** | NO_CB | 21.0% | 500 | 49.0% | 0 | - | - |
| **5** | SIMPLE_CB | 14.0% | 500 | 50.8% | 423 | - | - |
| **5** | AI_CB | 8.4% | 500 | 51.0% | 470 | - | - |
| **5** | ADAPTIVE_CB | 5.4% | 500 | 48.8% | 479 | - | - |
| **6** | NO_CB | 74.6% | 500 | 4.8% | 0 | - | - |
| **6** | SIMPLE_CB | 65.6% | 500 | 6.4% | - | - | - |
| **6** | AI_CB | 57.2% | 500 | 10.2% | - | - | - |
| **6** | ADAPTIVE_CB | 42.2% | 500 | 18.0% | - | - | - |

---

## CFR Reduction Summary

| Chain Length | NO_CB CFR | ADAPTIVE_CB CFR | Reduction (%) |
|--------------|-----------|---------------|--------------|
| 2 | 24.0% | 5.2% | **78%** |
| 3 | 22.2% | 4.2% | **81%** |
| 4 | 20.2% | 3.2% | **84%** |
| 5 | 21.0% | 5.4% | **74%** |
| 6 | 74.6% | 42.2% | **43%** |

---

## Key Findings

1. **ADAPTIVE_CB consistently performs best** across all chain lengths
2. **Peak benefit at 4 agents** (84% reduction)
3. **6-agent chains** show highest baseline CFR (74.6%) but CB still reduces by 43%
4. All circuit breakers significantly reduce cascading failures

---

## Reproduce These Results

```bash
cd agents/scholar/experiments/exp-001
python circuit_breaker_experiment.py --chain-length 2 --runs 500
python circuit_breaker_experiment.py --chain-length 3 --runs 500
python circuit_breaker_experiment.py --chain-length 4 --runs 500
python circuit_breaker_experiment.py --chain-length 5 --runs 500
python circuit_breaker_experiment.py --chain-length 6 --runs 500
```