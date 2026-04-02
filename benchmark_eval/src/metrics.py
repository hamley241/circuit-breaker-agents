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
            "utility": 0.0,
        }

    successes = sum(1 for t in traces if t.final_success)
    upstream_failures = sum(1 for t in traces if t.upstream_failure_seen)
    cascades = sum(1 for t in traces if t.cascade)
    failures = n - successes
    safe_failures = max(failures - cascades, 0)
    trip_count = sum(t.trip_count for t in traces)

    success_rate = successes / n
    upstream_failure_rate = upstream_failures / n
    cfr = (cascades / upstream_failures) if upstream_failures else 0.0
    safe_failure_rate = safe_failures / n
    avg_trip_count = trip_count / n
    catastrophic_failure_rate = cascades / n
    utility = success_rate - catastrophe_cost * catastrophic_failure_rate

    return {
        "runs": float(n),
        "success_rate": success_rate,
        "upstream_failure_rate": upstream_failure_rate,
        "cfr": cfr,
        "safe_failure_rate": safe_failure_rate,
        "avg_trip_count": avg_trip_count,
        "utility": utility,
    }
