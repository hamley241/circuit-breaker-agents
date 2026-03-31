from __future__ import annotations

from pathlib import Path
from typing import Iterable, Dict, Any
import json
import pandas as pd


def summarize_jsonl(jsonl_path: Path) -> pd.DataFrame:
    rows = []
    with jsonl_path.open() as f:
        for line in f:
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    group_cols = ["cb_type", "injection"]
    summary = df.groupby(group_cols).agg(
        runs=("run_id", "count"),
        upstream_failure_rate=("upstream_failure", "mean"),
        cascade_rate=("cascade", "mean"),
        final_success_rate=("final_success", "mean"),
        avg_breaker_trip_count=("breaker_trip_count", "mean"),
    ).reset_index()
    return summary
