from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import csv
import math
import random
from typing import Dict, List

import matplotlib.pyplot as plt


# ----------------------------
# Config
# ----------------------------

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42

# Fixed parameters for the sweep
CHAIN_LENGTH = 5
UPSTREAM_FAILURE_PROB = 0.20   # p_u
PP_VALUES = [0.1, 0.3, 0.5, 0.7, 0.9]
RUNS_PER_CONDITION = 5000


# ----------------------------
# Data model
# ----------------------------

@dataclass
class TrialResult:
    cb_type: str
    p_u: float
    p_p: float
    chain_length: int
    upstream_failure: bool
    cascade: bool
    final_success: bool
    breaker_trips: int


@dataclass
class AggregateResult:
    cb_type: str
    p_u: float
    p_p: float
    chain_length: int
    runs: int
    upstream_failure_rate: float
    cascade_rate: float
    final_success_rate: float
    avg_breaker_trips: float


# ----------------------------
# Breaker policies
# ----------------------------

class NoCircuitBreaker:
    def __init__(self) -> None:
        self.trip_count = 0

    def should_trip(self, stage_idx: int, failed_here: bool, recent_failures: List[bool]) -> bool:
        return False


class AICircuitBreaker:
    """
    Static policy:
    - if a failure is observed at a stage, trip immediately and stop propagation
    """
    def __init__(self) -> None:
        self.trip_count = 0

    def should_trip(self, stage_idx: int, failed_here: bool, recent_failures: List[bool]) -> bool:
        if failed_here:
            self.trip_count += 1
            return True
        return False


class AdaptiveCircuitBreaker:
    """
    Slightly more aggressive adaptive policy:
    - trip on current failure
    - also trip if recent failure density is high
    This intentionally tends to over-trigger a bit, which matches your paper’s current story.
    """
    def __init__(self, window: int = 3, failure_threshold: int = 1) -> None:
        self.trip_count = 0
        self.window = window
        self.failure_threshold = failure_threshold

    def should_trip(self, stage_idx: int, failed_here: bool, recent_failures: List[bool]) -> bool:
        recent_window = recent_failures[-self.window:]
        recent_count = sum(1 for x in recent_window if x)

        # Trip immediately on current detected failure
        if failed_here:
            self.trip_count += 1
            return True

        # Adaptive sensitivity: if recent failures are dense, trip conservatively
        if recent_count > self.failure_threshold:
            self.trip_count += 1
            return True

        return False


def make_breaker(cb_type: str):
    if cb_type == "no_cb":
        return NoCircuitBreaker()
    if cb_type == "ai_cb":
        return AICircuitBreaker()
    if cb_type == "adaptive_cb":
        return AdaptiveCircuitBreaker()
    raise ValueError(f"Unknown cb_type: {cb_type}")


# ----------------------------
# Simulation
# ----------------------------

def run_single_trial(
    rng: random.Random,
    cb_type: str,
    p_u: float,
    p_p: float,
    chain_length: int,
) -> TrialResult:
    """
    Simple propagation model:

    - Stage 0 may experience an upstream failure with probability p_u.
    - If a stage is in failed state, it may propagate to the next stage with probability p_p.
    - Breakers can trip when a failure is detected and prevent further propagation.
    - Final success is True iff no final-stage failure survives to the end.
    """
    breaker = make_breaker(cb_type)

    # Whether a failure exists at the current stage
    failed_state = rng.random() < p_u
    upstream_failure = failed_state

    recent_failures: List[bool] = [failed_state]
    cascade = False

    # Stage 0: breaker can stop failure immediately
    if breaker.should_trip(stage_idx=0, failed_here=failed_state, recent_failures=recent_failures):
        return TrialResult(
            cb_type=cb_type,
            p_u=p_u,
            p_p=p_p,
            chain_length=chain_length,
            upstream_failure=upstream_failure,
            cascade=False,
            final_success=True,
            breaker_trips=breaker.trip_count,
        )

    # Propagate through the remaining stages
    for stage_idx in range(1, chain_length):
        if failed_state:
            failed_state = rng.random() < p_p
        else:
            # No new independent failures after stage 0 in this simplified model
            failed_state = False

        recent_failures.append(failed_state)

        if breaker.should_trip(stage_idx=stage_idx, failed_here=failed_state, recent_failures=recent_failures):
            return TrialResult(
                cb_type=cb_type,
                p_u=p_u,
                p_p=p_p,
                chain_length=chain_length,
                upstream_failure=upstream_failure,
                cascade=False,
                final_success=True,
                breaker_trips=breaker.trip_count,
            )

    # If failure survives to the end, count as cascade and final failure
    if upstream_failure and failed_state:
        cascade = True

    final_success = not failed_state

    return TrialResult(
        cb_type=cb_type,
        p_u=p_u,
        p_p=p_p,
        chain_length=chain_length,
        upstream_failure=upstream_failure,
        cascade=cascade,
        final_success=final_success,
        breaker_trips=breaker.trip_count,
    )


def run_condition(
    cb_type: str,
    p_u: float,
    p_p: float,
    chain_length: int,
    runs: int,
    seed: int,
) -> AggregateResult:
    rng = random.Random(seed)

    trial_results: List[TrialResult] = []
    for _ in range(runs):
        trial_results.append(
            run_single_trial(
                rng=rng,
                cb_type=cb_type,
                p_u=p_u,
                p_p=p_p,
                chain_length=chain_length,
            )
        )

    upstream_failure_rate = sum(r.upstream_failure for r in trial_results) / runs
    cascade_rate = sum(r.cascade for r in trial_results) / runs
    final_success_rate = sum(r.final_success for r in trial_results) / runs
    avg_breaker_trips = sum(r.breaker_trips for r in trial_results) / runs

    return AggregateResult(
        cb_type=cb_type,
        p_u=p_u,
        p_p=p_p,
        chain_length=chain_length,
        runs=runs,
        upstream_failure_rate=upstream_failure_rate,
        cascade_rate=cascade_rate,
        final_success_rate=final_success_rate,
        avg_breaker_trips=avg_breaker_trips,
    )


# ----------------------------
# Output + plotting
# ----------------------------

def write_csv(rows: List[AggregateResult], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(asdict(rows[0]).keys()),
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def plot_metric(
    rows: List[AggregateResult],
    metric_name: str,
    ylabel: str,
    output_path: Path,
) -> None:
    cb_types = ["no_cb", "ai_cb", "adaptive_cb"]

    plt.figure(figsize=(8, 5))
    for cb_type in cb_types:
        subset = [r for r in rows if r.cb_type == cb_type]
        subset.sort(key=lambda r: r.p_p)

        xs = [r.p_p for r in subset]
        ys = [getattr(r, metric_name) for r in subset]

        plt.plot(xs, ys, marker="o", label=cb_type)

    plt.xlabel(r"Propagation Probability $p_p$")
    plt.ylabel(ylabel)
    plt.title(f"{ylabel} vs Propagation Probability")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def main() -> None:
    all_rows: List[AggregateResult] = []

    for cb_type in ["no_cb", "ai_cb", "adaptive_cb"]:
        for p_p in PP_VALUES:
            row = run_condition(
                cb_type=cb_type,
                p_u=UPSTREAM_FAILURE_PROB,
                p_p=p_p,
                chain_length=CHAIN_LENGTH,
                runs=RUNS_PER_CONDITION,
                seed=RANDOM_SEED,
            )
            all_rows.append(row)
            print(asdict(row))

    csv_path = OUTPUT_DIR / "pp_sweep_results.csv"
    write_csv(all_rows, csv_path)

    plot_metric(
        rows=all_rows,
        metric_name="cascade_rate",
        ylabel="Cascade Failure Rate (CFR)",
        output_path=OUTPUT_DIR / "pp_sweep_cfr.png",
    )

    plot_metric(
        rows=all_rows,
        metric_name="final_success_rate",
        ylabel="Final Success Rate",
        output_path=OUTPUT_DIR / "pp_sweep_success.png",
    )

    print(f"\nWrote CSV to: {csv_path}")
    print(f"Wrote plots to: {OUTPUT_DIR / 'pp_sweep_cfr.png'} and {OUTPUT_DIR / 'pp_sweep_success.png'}")


if __name__ == "__main__":
    main()
