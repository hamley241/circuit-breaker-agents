# exp-001b Analysis Charter (Draft)

> To be finalized before the full Modal run. Captures pre-registered success metrics and interpretation rules.

## Experiment
- **Name:** exp-001b — Circuit Breaker + Recovery Validation
- **Date Planned:** TBA (post diagnostics)
- **Workloads:** Green-path control + Stress routing task

## Primary Metrics
1. **Completion Delta:** (Completion rate per protection mode) − (Completion rate NO_PROTECTION)
2. **CFR Delta:** (CFR per protection mode) − (CFR NO_PROTECTION)

## Secondary Metrics
- Token efficiency (tokens per successful task)
- Recovery latency (time from trip to completion/fail)
- Time-to-trip distribution
- Protected Success Rate (PSR) = successes after at least one breaker event

## Interpretation Rules (to finalize)
- Minimum improvement thresholds
- Handling of simulator vs real discrepancies
- Reporting format for LinkedIn article

*Status: Draft — update after diagnostic phase to lock thresholds and acceptance criteria.*
