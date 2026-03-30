# Experiment 001: Circuit Breakers - Remaining Tasks for Publication

**Last Updated:** 2026-03-17  
**Status:** Post-Pilot / Pre-Submission  
**Estimated GPU Budget:** $25-30  

---

## ✅ Completed (March 13-16)

| Task | Status | Notes |
|------|--------|-------|
| Experiment design document | ✅ | 5 conditions defined, CFR operationalized |
| Circuit breaker implementation | ✅ | 4-state AI-aware + adaptive variants |
| Pilot results (simulated) | ✅ | 275 runs, n=55 per condition |
| Method section draft | ✅ | Ready for integration |
| Related Work (Mieczkowski + Patel) | ✅ | Full synthesis complete |

---

## 🟢 Recent Completions (March 19, 2026)

| Task | Status | Notes |
|------|--------|-------|
| **Real API Integration** | ✅ | GPT-4o calls working, Modal secrets wired, sim/real toggle implemented |
| **Cost Estimation** | ✅ | Full experiment ~$7, pilot ~$1.26, cost planning tools created |
| **Error Handling** | ✅ | Retry logic, graceful fallbacks, robust Modal deployment |
| **Real API Pilot Execution** | ✅ | 287s runtime, 100 calls, $1.26 cost, 100% success rate |
| **Documentation Updates** | ✅ | Modal guide, troubleshooting, cost notes from actual results |

## 🔴 Blockers (Must Clear Before Full Run)

| Blocker | Priority | Action Required | Owner |
|---------|----------|-----------------|-------|
| Consul re-review approval | P0 | Submit revised design for approval | Scholar |
| ~~GPU budget confirmation~~ | ~~P1~~ | ✅ **RESOLVED:** Real API costs only ~$7 | ~~Jimby~~ |

---

## 🟡 Remaining Experiments for Publication

### Required for arXiv Submission

| Experiment | Priority | API Cost | Status | Why Needed |
|------------|----------|----------|--------|------------|
| **Real API Validation** | P0 | ~~$20~~ $7 | ✅ **COMPLETE** | Actual GPT-4o calls to validate CFR claims |
| **LLM-as-judge Baseline** | P1 | $2 | ⏳ Ready to run | Compare CFRTracker vs. LLM judge for failure validation |
| **Statistical Significance Test** | P0 | $0 | ⏳ Pending data | Analysis: Dunnett's test, Cohen's h, confidence intervals |

### Stretch Goals (Nice to Have)

| Experiment | Priority | GPU Cost | Why Needed |
|------------|----------|----------|------------|
| **Ensemble Voting** | P2 | $8 | Multi-agent voting baseline comparison |
| **Long-Horizon Tasks** | P2 | $10 | Extend propagation window beyond 3 turns |
| **Heterogeneous Agents** | P3 | $15 | Cross-model team (GPT + Claude + Gemini) |
| **Pre-Execution Gate** | P3 | $5 | Test Patel et al.'s finding: pre-execution > post-execution |

---

## 📊 CFR Claims Validation Status

| Claim | Simulated | Real API | Status |
|-------|-----------|----------|--------|
| **66.7% CFR reduction** (AI_CB vs TIMEOUT_ONLY) | ✅ 0.2727 → 0.0909 | ❌ Needed | **BLOCKED** |
| **80% CFR reduction** (ADAPTIVE_CB) | ✅ 0.2727 → 0.0545 | ❌ Needed | **BLOCKED** |

**Note:** Current results from `exp-001-results.json` are simulated (elapsed 0.016s for 275 runs).

---

## 📝 Task Breakdown

### Task 1: Real API Validation Run (P0)

**Goal:** Run actual GPT-4o calls to validate CFR reduction claims.

**Sample:** 275 runs (5 conditions × 55) OR reduce to 150 runs (5 × 30) for cost

**Success Criteria:**
- CFR reduction ≥ 30% for AI_CB vs TIMEOUT_ONLY
- Statistical significance: p < 0.05 (Dunnett's test)
- Cohen's h ≥ 0.25 (medium effect)

**Risk Mitigation:**
- If real CFR < 10% (floor): Reduce failure injection rate
- If real CFR > 80% (ceiling): Increase task difficulty

**Files:**
- Update: `experiment_runner.py` with real API calls
- Create: `exp-001-real-results.json`

---

### Task 2: LLM-as-Judge Baseline (P1)

**Goal:** Compare CFRTracker (external measurement) vs LLM-as-judge (agent self-assessment) to validate our claim that external measurement is essential.

**Key Question:** Does LLM-as-judge inherit overconfidence bias per Patel et al.?

**Method:**
1. Run 50 tasks with known failures
2. Have GPT-4o judge: "Did Agent A fail? Will Agent B fail?"
3. Compare predictions vs actual failures
4. Calculate calibration error (predicted success - actual success)

**Expected Finding:** LLM judge overpredicts success (replicating Patel et al.)

**File:** `experiments/exp-001/llm_judge_baseline.py`

---

### Task 3: Statistical Analysis (P0)

**Goal:** Complete statistical analysis on real/simulated data.

**Analyses Needed:**
```python
# Primary: Dunnett's test (each treatment vs control)
- H0: CFR_treatment = CFR_timeout_only
- Alpha = 0.05 (adjusted)
- Report: t-statistic, p-value, 95% CI

# Secondary: Effect size
- Cohen's h for CFR proportion differences
- Odds ratio: Treatment vs TIMEOUT_ONLY
- NNT: "Need X tasks to prevent 1 cascade"

# Sensitivity: Bootstrap 95% CI
- 1000 resamples
- Report robustness
```

**Files:**
- Create: `experiments/exp-001/statistical_analysis.py`
- Output: `exp-001-statistics.json`

---

### Task 4: Visualization (P1)

**Goal:** Create publication-ready figures.

| Figure | Description | Priority |
|--------|-------------|----------|
| Fig 1 | CFR by condition (bar chart) | P0 |
| Fig 2 | Recovery time distributions | P1 |
| Fig 3 | State transition diagram | P0 |
| Fig 4 | Princeton metrics trajectory | P1 |
| Fig 5 | Calibration: LLM judge vs CFRTracker | P2 |

**Tools:** Matplotlib / Seaborn / Plotly
**Style:** NEURIPS / ICML workshop format

---

### Task 5: Adversarial Assessment Implementation (P2)

**Goal:** Implement adversarial bug-finding mode per Patel et al.'s finding.

**Implementation:**
```python
def adversarial_check(response: Response) -> bool:
    """Use bug-finding prompt to reduce overconfidence by 15pp."""
    prompt = """Find bugs or flaws in this reasoning.
    Response: {response.reasoning}
    List 3 potential errors:"""
    # Return True if errors found (trip circuit)
    # Implements Patel et al.'s adversarial reframe
```

Integrate into `CONFIDENCE_HALF_OPEN` recovery testing.

---

### Task 6: Pre-Execution Gate Exploration (P3)

**Goal:** Test Patel et al.'s counterintuitive finding that pre-execution assessment > post-execution.

**Hypothesis:** Pre-execution risk gate improves CFR over post-hoc detection.

**Method:**
- Add `pre_execution_gate()` that assesses task risk before agent assignment
- Compare CFR with/without pre-gate
- Measure: Does discriminating power (AUROC) improve?

---

## 📅 Revised Timeline

| Phase | Task | Duration | Due | Status |
|-------|------|----------|-----|--------|
| 2a | Consul approval + GPU budget | 1 day | Mar 17 | 🔴 BLOCKED |
| 2b | Real API validation | 1 day | Mar 18 | ⏳ Pending |
| 2c | Statistical analysis + viz | 1 day | Mar 19 | ⏳ Pending |
| 2d | LLM judge baseline | 0.5 day | Mar 19 | ⏳ Pending |
| 3a | Write Results section | 1 day | Mar 20 | ⏳ Pending |
| 3b | Write Discussion/Conclusion | 1 day | Mar 21 | ⏳ Pending |
| 3c | Full draft review | 1 day | Mar 22 | ⏳ Pending |
| 4 | Submit to arXiv | 1 day | Mar 23 | ⏳ Pending |

**Total remaining:** ~6 days work (ends Mar 23)

---

## 💰 Budget Summary

| Task | Estimated Cost |
|------|----------------|
| Real API validation (150 runs) | $15 |
| LLM-as-judge baseline (50 runs) | $5 |
| Ensemble voting | $8 |
| **Minimum for publication** | **$20** |
| **Stretch goals included** | **$28** |

---

## 🏁 Go/No-Go Decision Criteria

**Proceed to Full Submission If:**
- ✅ Real API validation shows ≥ 30% CFR reduction
- ✅ Statistical significance p < 0.05
- ✅ Cohen's h ≥ 0.5 (large effect)

**Pivot to Alternative If:**
- ❌ Real CFR reduction < 20% → Consider simulator-only preprint
- ❌ Cannot secure GPU budget → Reduce scope to n=30/condition
- ❌ LLM judge baseline shows CFRTracker has bias → Methods revision

---

## 🤝 Cross-References

| File | Purpose |
|------|---------|
| `circuit-breaker-paper-outline.md` | Full paper outline |
| `draft-method.md` | Method section ready |
| `plan-001.md` | High-level project tracking |
| `exp-001-results.json` | Pilot results (simulated) |

---

**Last Updated:** 2026-03-17 by Scholar Agent  
**Next Review:** After Consul approval + GPU budget confirmed
