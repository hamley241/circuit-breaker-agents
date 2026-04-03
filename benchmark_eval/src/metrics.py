from __future__ import annotations

from typing import Dict, List

from .schemas import RunTrace


def summarize_traces(traces: List[RunTrace], catastrophe_cost: float) -> Dict[str, float]:
    n = len(traces)
    if n == 0:
        return {
            "runs": 0,
            "success_rate": 0.0,
            "upstream_failure_rate": 0.0,
            "cfr": 0.0,
            "safe_failure_rate": 0.0,
            "avg_trip_count": 0.0,
            "corrupted": 0.0,
            "clean": 0.0,
            "cascades": 0.0,
            "corrupted_and_cascade": 0.0,
            "clean_and_cascade": 0.0,
            "cfr_injected": 0.0,
            "cfr_clean": 0.0,
            "lift": 0.0,
            "utility": 0.0,
        }

    successes = sum(1 for t in traces if t.final_success)
    upstream_failures = sum(1 for t in traces if t.upstream_failure_seen)
    cascades = sum(1 for t in traces if t.cascade)
    failures = n - successes
    safe_failures = max(failures - cascades, 0)
    corrupted = sum(1 for t in traces if t.upstream_corrupted)
    clean = sum(1 for t in traces if not t.upstream_corrupted)
    corrupted_and_cascade = sum(1 for t in traces if t.upstream_corrupted and t.cascade)
    clean_and_cascade = sum(1 for t in traces if (not t.upstream_corrupted) and t.cascade)
    trip_count = sum(t.trip_count for t in traces)

    success_rate = successes / n
    upstream_failure_rate = upstream_failures / n
    cfr = (cascades / upstream_failures) if upstream_failures else 0.0
    safe_failure_rate = safe_failures / n
    avg_trip_count = trip_count / n
    cfr_injected = (corrupted_and_cascade / corrupted) if corrupted else 0.0
    cfr_clean = (clean_and_cascade / clean) if clean else 0.0
    lift = cfr_injected - cfr_clean
    catastrophic_failure_rate = cascades / n
    utility = success_rate - catastrophe_cost * catastrophic_failure_rate

    return {
        "runs": float(n),
        "success_rate": success_rate,
        "upstream_failure_rate": upstream_failure_rate,
        "cfr": cfr,
        "safe_failure_rate": safe_failure_rate,
        "avg_trip_count": avg_trip_count,
        "corrupted": float(corrupted),
        "clean": float(clean),
        "cascades": float(cascades),
        "corrupted_and_cascade": float(corrupted_and_cascade),
        "clean_and_cascade": float(clean_and_cascade),
        "cfr_injected": cfr_injected,
        "cfr_clean": cfr_clean,
        "lift": lift,
        "utility": utility,
    }
