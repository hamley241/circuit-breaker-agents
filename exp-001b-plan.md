# exp-001b — Reliability Pattern #2 Follow-Up

## Objectives
- Demonstrate measurable reliability gains (completion + CFR deltas) using circuit breakers paired with explicit recovery policies.
- Produce publication-grade evidence for LinkedIn “Reliability Pattern #2” referencing both control (green-path) and stress workloads.
- Keep an auditable trail: diagnostic mini-run → simulator-backed config → full Modal sweep.

## Scope
1. **Workloads**
   - **Control (Green-Path):** Deterministic task that must succeed (e.g., structured retrieval with known answer). Purpose: validate infrastructure + recovery logic.
   - **Stress Routing Task:** Original multi-agent routing scenario, updated to allow ≥25 turns + recovery hooks.

2. **Protection Modes & Recovery Policies**
| Condition      | Protection Mechanism           | Recovery Policy (triggered on failure / OPEN state) |
|----------------|--------------------------------|------------------------------------------------------|
| NO_PROTECTION  | None                           | None                                                 |
| TIMEOUT_ONLY   | Hard timeout on agent calls    | Retry once, then fail subtask                        |
| SIMPLE_CB      | Fixed thresholds               | Skip failing agent, continue with remaining plan     |
| AI_CB          | Reasoning-aware breaker        | Alternate prompt/model (Claude ↔ GPT-4o)             |
| ADAPTIVE_CB    | Predictive thresholds          | Route to “safe-mode” workflow with degraded objectives |

3. **Budgets & Metrics**
- Turn budget per run: **≥25** turns.
- Runs per condition (full sweep): **10** (after diagnostics pass).
- Metrics to log per run:
  - Completion rate, CFR, “Protected Success Rate (PSR)”
  - Time-to-trip, number of trips, recovery attempts + outcomes
  - Token burn (total + per agent), latency distribution
  - Timeline of events (trip → mitigation → final status)

4. **Simulator Harness**
- Implement local simulator that mirrors Modal logic with stubbed LLM responses.
- Use for iterative tuning of breaker thresholds + recovery policies before Modal spend.

5. **Diagnostics Phase (pre-flight)**
- Execute **2 runs per condition** (control + stress) with enhanced logging to categorize current failure modes.
- Criteria to proceed: control task succeeds ≥95% in CB conditions; stress task shows non-zero completion under at least one protection mode in simulator.

6. **Analysis Charter (pre-register)**
- **Primary metrics:** Completion delta vs NO_PROTECTION, CFR delta.
- **Secondary metrics:** Token efficiency, recovery latency, time-to-trip.
- Publish charter summary in `agents/scholar/experiments/exp-001/analysis-charter.md` before full Modal run.

7. **Artifacts & Reporting**
- Update `EXPERIMENT_LOG.md` after every diagnostic + real run.
- Store raw outputs under `agents/scholar/experiments/exp-001/results/exp-001b-*.json`.
- Capture plots/tables for LinkedIn article (completion vs mode, recovery outcomes, timeline examples).

## Task Breakdown
1. **Simulator Build**
   - [ ] Implement stubbed LLM responses + breaker state machine parity
   - [ ] Configurable turn budget + recovery hooks
   - [ ] CLI parity with Modal command flags

2. **Workload Prep**
   - [ ] Control task prompt + checker
   - [ ] Stress task upgrade (≥25 turns, recovery hooks)

3. **Recovery Policy Implementations**
   - [ ] Timeout retry logic
   - [ ] Skip-and-continue handler
   - [ ] Alternate model swapper
   - [ ] Safe-mode workflow definition

4. **Instrumentation**
   - [ ] Per-run timeline logging
   - [ ] Token + latency accounting
   - [ ] Recovery outcome recorder

5. **Diagnostics Run**
   - [ ] Execute 2 runs/condition (control + stress)
   - [ ] Analyze failure modes, adjust prompts/policies if needed

6. **Analysis Charter**
   - [ ] Draft + commit charter file

7. **Full Modal Run**
   - [ ] Execute simulator-backed config on Modal real mode
   - [ ] Save results JSON + update ledger + prep visuals

8. **Publication Prep**
   - [ ] Feed results into LinkedIn article + supporting assets

## Status
- Ledger initialized (`EXPERIMENT_LOG.md`).
- Pending: simulator, workloads, diagnostics, charter, Modal run.
