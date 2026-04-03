from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from .metrics import summarize_traces
from .schemas import RunTrace


LABELS = {
    "no_cb": "No CB",
    "ai_cb": "AI-guided CB",
    "adaptive_cb": "Adaptive CB",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize raw benchmark traces.")
    parser.add_argument("--input", required=True, help="Raw JSONL trace file.")
    parser.add_argument("--output-csv", required=True, help="Summary CSV output path.")
    parser.add_argument("--output-tex", required=True, help="LaTeX table output path.")
    parser.add_argument("--catastrophe-cost", type=float, default=5.0)
    return parser.parse_args()


def load_traces(path: Path) -> List[RunTrace]:
    traces: List[RunTrace] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                traces.append(RunTrace.model_validate(json.loads(line)))
    return traces


def to_csv(rows: List[Dict[str, str]]) -> str:
    headers = [
        "policy",
        "label",
        "runs",
        "success_rate",
        "upstream_failure_rate",
        "cfr",
        "safe_failure_rate",
        "avg_trip_count",
        "corrupted",
        "clean",
        "cascades",
        "corrupted_and_cascade",
        "clean_and_cascade",
        "cfr_injected",
        "cfr_clean",
        "lift",
        "utility",
    ]
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(str(row[h]) for h in headers))
    return "\n".join(lines) + "\n"


def to_latex(rows: List[Dict[str, str]], cost: float) -> str:
    cost_label = int(cost) if float(cost).is_integer() else cost
    lines = []
    lines.append("\\begin{tabular}{lrrrrrr}")
    lines.append("\\toprule")
    lines.append(
        "Method & Success $\\uparrow$ & CFR $\\downarrow$ & CFR Injected & CFR Clean & Lift & Utility ($c={}$) $\\uparrow$ \\\\".format(cost_label)
    )
    lines.append("\\midrule")
    for row in rows:
        lines.append(
            "{} & {:.3f} & {:.3f} & {:.3f} & {:.3f} & {:.3f} & {:.3f} \\\\".format(
                row["label"],
                float(row["success_rate"]),
                float(row["cfr"]),
                float(row["cfr_injected"]),
                float(row["cfr_clean"]),
                float(row["lift"]),
                float(row["utility"]),
            )
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    traces = load_traces(Path(args.input))
    by_policy: Dict[str, List[RunTrace]] = {}
    for trace in traces:
        by_policy.setdefault(trace.policy, []).append(trace)

    rows: List[Dict[str, str]] = []
    for policy in ["no_cb", "ai_cb", "adaptive_cb"]:
        traces_for_policy = by_policy.get(policy, [])
        summary = summarize_traces(traces_for_policy, catastrophe_cost=args.catastrophe_cost)
        rows.append(
            {
                "policy": policy,
                "label": LABELS.get(policy, policy),
                "runs": int(summary["runs"]),
                "success_rate": f"{summary['success_rate']:.6f}",
                "upstream_failure_rate": f"{summary['upstream_failure_rate']:.6f}",
                "cfr": f"{summary['cfr']:.6f}",
                "safe_failure_rate": f"{summary['safe_failure_rate']:.6f}",
                "avg_trip_count": f"{summary['avg_trip_count']:.6f}",
                "corrupted": int(summary["corrupted"]),
                "clean": int(summary["clean"]),
                "cascades": int(summary["cascades"]),
                "corrupted_and_cascade": int(summary["corrupted_and_cascade"]),
                "clean_and_cascade": int(summary["clean_and_cascade"]),
                "cfr_injected": f"{summary['cfr_injected']:.6f}",
                "cfr_clean": f"{summary['cfr_clean']:.6f}",
                "lift": f"{summary['lift']:.6f}",
                "utility": f"{summary['utility']:.6f}",
            }
        )

    csv_path = Path(args.output_csv)
    tex_path = Path(args.output_tex)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(to_csv(rows), encoding="utf-8")
    tex_path.write_text(to_latex(rows, args.catastrophe_cost), encoding="utf-8")
    print(f"Wrote summary CSV to {csv_path}")
    print(f"Wrote LaTeX table to {tex_path}")


if __name__ == "__main__":
    main()
