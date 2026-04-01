#!/usr/bin/env python3
"""
Propagation Probability Sensitivity Sweep for Circuit Breaker Agents
==================================================================

This simulation is designed to match the paper's scientific claim:
failures can propagate across stages, and circuit breakers reduce
effective propagation.

Key modeling choices:
- p_u: intrinsic upstream failure probability
- p_p: propagation probability if prior stage failed
- breakers have imperfect detection (not perfect oracles)
- adaptive breaker is slightly more aggressive and may over-trigger

Outputs:
- outputs/pp_sweep_results.csv
- outputs/pp_sweep_results.json
- outputs/pp_sweep_cfr.png
- outputs/pp_sweep_success.png
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any

import matplotlib.pyplot as plt


# ----------------------------
# Configuration
# ----------------------------

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42

# Sweep settings
PP_VALUES = [0.1, 0.3, 0.5, 0.7, 0.9]
PU = 0.20
CHAIN_LENGTH = 5
RUNS_PER_CONDITION = 5000


# ----------------------------
# Data models
# ----------------------------

class CBType(Enum):
    NO_CB = "no_cb"
    AI_CB = "ai_cb"
    ADAPTIVE_CB = "adaptive_cb"


@dataclass
class AgentStep:
    stage_idx: int
    intrinsic_failure_used: bool
    propagated_failure_used: bool
    failed: bool
    breaker_allowed: bool
    breaker_tripped: bool
    confidence: float


@dataclass
class TrialResult:
    cb_type: str
    p_u: float
    p_p: float
    chain_length: int
    upstream_failure: bool
    cascade_failure: bool
    final_success: bool
    breaker_trips: int
    steps: List[AgentStep]


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
# Circuit breaker policies
# ----------------------------

class BaseCircuitBreaker:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.trip_count = 0

    def should_trip(
        self,
        stage_idx: int,
        failed_here: bool,
        confidence: float,
        recent_failures: List[bool],
    ) -> bool:
        raise NotImplementedError


class NoCircuitBreaker(BaseCircuitBreaker):
    def should_trip(
        self,
        stage_idx: int,
        failed_here: bool,
        confidence: float,
        recent_failures: List[bool],
    ) -> bool:
        return False


class AICircuitBreaker(BaseCircuitBreaker):
    """
    Static AI-based breaker with imperfect detection.

    detection_prob:
        Probability of catching a real failure when it appears.

    false_positive_prob:
        Small chance of tripping even on a non-failure, to reflect noisy judgment.
    """
    def __init__(
        self,
        rng: random.Random,
        detection_prob: float = 0.80,
        false_positive_prob: float = 0.02,
        confidence_threshold: float = 0.45,
    ) -> None:
        super().__init__(rng)
        self.detection_prob = detection_prob
        self.false_positive_prob = false_positive_prob
        self.confidence_threshold = confidence_threshold

    def should_trip(
        self,
        stage_idx: int,
        failed_here: bool,
        confidence: float,
        recent_failures: List[bool],
    ) -> bool:
        # Catch real failures with imperfect detection
        if failed_here:
            low_confidence_bonus = 0.10 if confidence < self.confidence_threshold else 0.0
            if self.rng.random() < min(1.0, self.detection_prob + low_confidence_bonus):
                self.trip_count += 1
                return True

        # Rare false positive
        if (not failed_here) and self.rng.random() < self.false_positive_prob:
            self.trip_count += 1
            return True

        return False


class AdaptiveCircuitBreaker(BaseCircuitBreaker):
    """
    More aggressive breaker:
    - imperfectly detects real failures
    - trips more readily when recent failures are dense
    - slightly more false positives than AI_CB
    """
    def __init__(
        self,
        rng: random.Random,
        base_detection_prob: float = 0.80, #0.85,
        false_positive_prob: float = 0.08, # 0.04,
        window: int = 3,
        density_threshold: int = 1,
        confidence_threshold: float = 0.55,
    ) -> None:
        super().__init__(rng)
        self.base_detection_prob = base_detection_prob
        self.false_positive_prob = false_positive_prob
        self.window = window
        self.density_threshold = density_threshold
        self.confidence_threshold = confidence_threshold

    def should_trip(
        self,
        stage_idx: int,
        failed_here: bool,
        confidence: float,
        recent_failures: List[bool],
    ) -> bool:
        recent_window = recent_failures[-self.window:] if recent_failures else []
        recent_failure_count = sum(recent_window)

        # More aggressive detection when recent failures accumulate
        adaptive_bonus = 0.10 if recent_failure_count > self.density_threshold else 0.0
        confidence_bonus = 0.10 if confidence < self.confidence_threshold else 0.0

        if failed_here:
            if self.rng.random() < min(1.0, self.base_detection_prob + adaptive_bonus + confidence_bonus):
                self.trip_count += 1
                return True

        # Slightly higher false positive rate under "nervous" conditions
        false_positive = self.false_positive_prob + (0.05 if recent_failure_count > self.density_threshold else 0.0)
        #false_positive = self.false_positive_prob + (0.02 if recent_failure_count > self.density_threshold else 0.0)
        if (not failed_here) and self.rng.random() < false_positive:
            self.trip_count += 1
            return True

        return False


def make_breaker(cb_type: CBType, rng: random.Random) -> BaseCircuitBreaker:
    if cb_type == CBType.NO_CB:
        return NoCircuitBreaker(rng)
    if cb_type == CBType.AI_CB:
        return AICircuitBreaker(rng)
    if cb_type == CBType.ADAPTIVE_CB:
        return AdaptiveCircuitBreaker(rng)
    raise ValueError(f"Unsupported cb_type: {cb_type}")


# ----------------------------
# Simulation logic
# ----------------------------

def run_single_trial(
    rng: random.Random,
    cb_type: CBType,
    p_u: float,
    p_p: float,
    chain_length: int,
) -> TrialResult:
    """
    Scientific model:
    - Stage 0 can fail intrinsically with probability p_u
    - For stage i > 0:
        - if previous stage failed, current stage fails with probability p_p (propagation)
        - otherwise it fails intrinsically with probability p_u
    - breaker can trip on any stage and prevent further propagation
    """
    breaker = make_breaker(cb_type, rng)
    steps: List[AgentStep] = []
    recent_failures: List[bool] = []

    upstream_failure = False
    cascade_failure = False
    final_success = True

    previous_failed = False
    breaker_stopped = False

    for stage_idx in range(chain_length):
        # If breaker has already stopped execution, remaining stages are not run
        if breaker_stopped:
            break

        confidence = rng.uniform(0.3, 0.95)

        if stage_idx == 0:
            intrinsic_failure_used = True
            propagated_failure_used = False
            failed_here = rng.random() < p_u
            upstream_failure = failed_here
        else:
            if previous_failed:
                intrinsic_failure_used = False
                propagated_failure_used = True
                failed_here = rng.random() < p_p
            else:
                intrinsic_failure_used = True
                propagated_failure_used = False
                failed_here = rng.random() < p_u

        # Circuit breaker decides whether to halt execution at this stage
        breaker_tripped = breaker.should_trip(
            stage_idx=stage_idx,
            failed_here=failed_here,
            confidence=confidence,
            recent_failures=recent_failures,
        )

        steps.append(
            AgentStep(
                stage_idx=stage_idx,
                intrinsic_failure_used=intrinsic_failure_used,
                propagated_failure_used=propagated_failure_used,
                failed=failed_here,
                breaker_allowed=not breaker_tripped,
                breaker_tripped=breaker_tripped,
                confidence=confidence,
            )
        )

        recent_failures.append(failed_here)

        if breaker_tripped:
            breaker_stopped = True
            final_success = True
            cascade_failure = False
            break

        # True cascade means an upstream failure actually propagated and survived
        if stage_idx > 0 and previous_failed and failed_here:
            cascade_failure = True

        previous_failed = failed_here

    # If final executed stage failed and was not blocked, task fails
    if not breaker_stopped and steps:
        final_success = not steps[-1].failed

    return TrialResult(
        cb_type=cb_type.value,
        p_u=p_u,
        p_p=p_p,
        chain_length=chain_length,
        upstream_failure=upstream_failure,
        cascade_failure=cascade_failure,
        final_success=final_success,
        breaker_trips=breaker.trip_count,
        steps=steps,
    )


def aggregate_trials(
    cb_type: CBType,
    p_u: float,
    p_p: float,
    chain_length: int,
    trials: List[TrialResult],
) -> AggregateResult:
    runs = len(trials)
    return AggregateResult(
        cb_type=cb_type.value,
        p_u=p_u,
        p_p=p_p,
        chain_length=chain_length,
        runs=runs,
        upstream_failure_rate=sum(t.upstream_failure for t in trials) / runs,
        cascade_rate=sum(t.cascade_failure for t in trials) / runs,
        final_success_rate=sum(t.final_success for t in trials) / runs,
        avg_breaker_trips=sum(t.breaker_trips for t in trials) / runs,
    )


def run_condition(
    cb_type: CBType,
    p_u: float,
    p_p: float,
    chain_length: int,
    runs: int,
    seed: int,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    trials: List[TrialResult] = []

    for _ in range(runs):
        trials.append(
            run_single_trial(
                rng=rng,
                cb_type=cb_type,
                p_u=p_u,
                p_p=p_p,
                chain_length=chain_length,
            )
        )

    agg = aggregate_trials(cb_type, p_u, p_p, chain_length, trials)
    return {
        "aggregate": agg,
        "trials": trials,
    }


# ----------------------------
# Output helpers
# ----------------------------

def write_csv(rows: List[AggregateResult], path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_json(results: List[Dict[str, Any]], path: Path) -> None:
    serializable = []
    for result in results:
        serializable.append(
            {
                "aggregate": asdict(result["aggregate"]),
                "trials": [
                    {
                        **asdict(trial),
                        "steps": [asdict(step) for step in trial.steps],
                    }
                    for trial in result["trials"][:50]  # cap stored raw trials
                ],
            }
        )

    with path.open("w") as f:
        json.dump(serializable, f, indent=2)


def plot_metric(
    rows: List[AggregateResult],
    metric_name: str,
    ylabel: str,
    title: str,
    output_path: Path,
) -> None:
    plt.figure(figsize=(8, 5))

    for cb_type in ["no_cb", "ai_cb", "adaptive_cb"]:
        subset = [r for r in rows if r.cb_type == cb_type]
        subset.sort(key=lambda r: r.p_p)

        xs = [r.p_p for r in subset]
        ys = [getattr(r, metric_name) for r in subset]

        plt.plot(xs, ys, marker="o", label=cb_type)

    plt.xlabel(r"Propagation Probability $p_p$")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


# ----------------------------
# Main
# ----------------------------

def main() -> None:
    all_condition_results: List[Dict[str, Any]] = []
    aggregate_rows: List[AggregateResult] = []

    for cb_type in [CBType.NO_CB, CBType.AI_CB, CBType.ADAPTIVE_CB]:
        for p_p in PP_VALUES:
            result = run_condition(
                cb_type=cb_type,
                p_u=PU,
                p_p=p_p,
                chain_length=CHAIN_LENGTH,
                runs=RUNS_PER_CONDITION,
                seed=SEED,
            )
            all_condition_results.append(result)
            aggregate_rows.append(result["aggregate"])

            agg = result["aggregate"]
            print(
                f"{agg.cb_type:12s} "
                f"p_u={agg.p_u:.2f} "
                f"p_p={agg.p_p:.2f} "
                f"runs={agg.runs:<5d} "
                f"upstream={agg.upstream_failure_rate:.4f} "
                f"cascade={agg.cascade_rate:.4f} "
                f"success={agg.final_success_rate:.4f} "
                f"trips={agg.avg_breaker_trips:.4f}"
            )

    csv_path = OUTPUT_DIR / "pp_sweep_results.csv"
    json_path = OUTPUT_DIR / "pp_sweep_results.json"
    cfr_plot_path = OUTPUT_DIR / "pp_sweep_cfr.png"
    success_plot_path = OUTPUT_DIR / "pp_sweep_success.png"

    write_csv(aggregate_rows, csv_path)
    write_json(all_condition_results, json_path)

    plot_metric(
        rows=aggregate_rows,
        metric_name="cascade_rate",
        ylabel="Cascade Failure Rate (CFR)",
        title="Sensitivity to Propagation Probability",
        output_path=cfr_plot_path,
    )

    plot_metric(
        rows=aggregate_rows,
        metric_name="final_success_rate",
        ylabel="Final Success Rate",
        title="Success vs Propagation Probability",
        output_path=success_plot_path,
    )

    print(f"\nWrote CSV:    {csv_path}")
    print(f"Wrote JSON:   {json_path}")
    print(f"Wrote figure: {cfr_plot_path}")
    print(f"Wrote figure: {success_plot_path}")


if __name__ == "__main__":
    main()
