# Code Versioning Protocol

## The Problem
- Multiple versions of same code
- Can't reproduce earlier working results  
- Changes get lost in confusion

## The Protocol

### Before Any Code Changes

1. **Save current as v{n}.py**
   ```bash
   cp run_experiment.py run_experiment_v1.py
   ```

2. **Make changes in NEW file**
   ```bash
   cp run_experiment_v1.py run_experiment_v2.py
   # Edit v2
   ```

3. **Test v2 before running experiments**
   - Smoke test (100 runs)
   - Verify against known-good data

4. **Only swap to v2 after passing test**
   - Compare results to v1 or baseline

### Version Naming

| Version | Date | Status | Notes |
|----------|------|--------|-------|
| v1 | 2026-03-30 | Baseline | First working |
| v2 | - | Working | Fixes from v1 |

### When to Create New Version

- Before any logic changes
- Before parameter changes
- When results change unexpectedly

### What to Include in Header

```python
"""
Run Experiment v{n}
Date: YYYY-MM-DD
Status: [WORKING/BROKEN/TESTING]
Based on: v{n-1} with [description of changes]
Smoke test: [PASS/FAIL] [date]
"""
```

### Smoketest Command

```bash
python3 run_experiment_v{n}.py --chain-length 3 --runs 100
```

Expected: ~15-25% NO_CB, ~3-5% ADAPTIVE (for 3 chains)

---

## Current State (March 30, 2026)

- Working results: RESULTS_VALIDATED.md
  - NO_CB: 22.9%
  - ADAPTIVE_CB: 4.6% (80% reduction)
  
- Script: run_experiment.py (BROKEN - needs rewrite from validated pattern)

## Next Steps

1. Copy RESULTS_VALIDATED as v1
2. Rebuild v2 from pattern that matches
3. Test before full run