#!/usr/bin/env python3
"""
simulate_circuit_breakers.py

A simple simulation for LLM circuit breakers with:
- intrinsic failure probability: p_u
- propagation probability: p_p
- imperfect fallback success after trip: p_f

Modes:
- no_cb
- ai_cb
- adaptive_cb

Goal:
Create a realistic tradeoff where adaptive_cb can achieve:
- lower catastrophic failure rate (CFR)
- but also lower success rate
because it trips more aggressively and fallback is imperfect.

Example:
    python simulate_circuit_breakers.py --runs 5000
"""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple


# -----------------------------
# Data structures
# -----------------------------

@dataclass
class Policy:
    name: str
    threshold: float
    base_threshold: float | None = None
    adapt_gamma: float = 0.0


@dataclass
class RunResult:
    mode: str
    p_u: float
    p_p: float
    runs: int
    success_rate: float
    safe_fail_rate: float
    catastrophic_fail_rate: float
    trip_rate: float
    upstream_issue_rate: float
    recoverable_issue_rate: float
    risky_issue_rate: float
    utility: float

@dataclass
class Counts:
    success: int = 0
    safe_fail: int = 0
    catastrophic_fail: int = 0
    trips: int = 0
    upstream_issues: int = 0
    recoverable_issues: int = 0
    risky_issues: int = 0


# -----------------------------
# Core simulation model
# -----------------------------

class CircuitBreakerSimulation:
    """
    Model overview

    For each request:
    1. With probability p_u, an upstream issue occurs.
    2. Conditional on an issue:
       - with probability p_p, it is risky and may catastrophically propagate
       - with probability (1 - p_p), it is recoverable
    3. The breaker sees a noisy score, not ground truth.
    4. If breaker trips:
       - fallback succeeds with probability p_f
       - otherwise safe_fail
    5. If breaker does not trip:
       - risky issue -> catastrophic_fail
       - recoverable issue -> succeeds with probability recoverable_continue_success
       - no issue -> success

    This creates the safety/availability tradeoff:
    - aggressive tripping lowers CFR
    - but trips can reduce success because fallback is imperfect
    """

    def __init__(
        self,
        seed: int,
        p_f: float,
        recoverable_continue_success: float,
        healthy_score_mean: float,
        recoverable_score_mean: float,
        risky_score_mean: float,
        score_std: float,
        adaptive_base_threshold: float,
        adaptive_gamma: float,
        ai_threshold: float,
    ) -> None:
        self.rng = random.Random(seed)

        self.p_f = p_f
        self.recoverable_continue_success = recoverable_continue_success

        self.healthy_score_mean = healthy_score_mean
        self.recoverable_score_mean = recoverable_score_mean
        self.risky_score_mean = risky_score_mean
        self.score_std = score_std

        self.ai_policy = Policy(
            name="ai_cb",
            threshold=ai_threshold,
        )

        self.adaptive_policy = Policy(
            name="adaptive_cb",
            threshold=adaptive_base_threshold,
            base_threshold=adaptive_base_threshold,
            adapt_gamma=adaptive_gamma,
        )

        self.no_cb_policy = Policy(
            name="no_cb",
            threshold=float("inf"),
        )

    def sample_score(self, issue_type: str) -> float:
        if issue_type == "healthy":
            mu = self.healthy_score_mean
        elif issue_type == "recoverable":
            mu = self.recoverable_score_mean
        elif issue_type == "risky":
            mu = self.risky_score_mean
        else:
            raise ValueError(f"Unknown issue type: {issue_type}")

        return self.rng.gauss(mu, self.score_std)

    def get_adaptive_threshold(self, p_p: float) -> float:
        """
        Adaptive policy lowers its threshold as propagation risk rises.
        Lower threshold => more aggressive tripping.
        """
        assert self.adaptive_policy.base_threshold is not None
        threshold = self.adaptive_policy.base_threshold - self.adaptive_policy.adapt_gamma * p_p
        return max(0.0, min(1.0, threshold))

    def should_trip(self, mode: str, score: float, p_p: float) -> bool:
        if mode == "no_cb":
            return False
        if mode == "ai_cb":
            return score >= self.ai_policy.threshold
        if mode == "adaptive_cb":
            threshold = self.get_adaptive_threshold(p_p)
            return score >= threshold

        raise ValueError(f"Unknown mode: {mode}")

    def simulate_one_request(self, mode: str, p_u: float, p_p: float) -> Tuple[str, bool, str]:
        """
        Returns:
            outcome: one of {"success", "safe_fail", "catastrophic_fail"}
            trip: whether breaker tripped
            issue_type: one of {"healthy", "recoverable", "risky"}
        """
        upstream_issue = self.rng.random() < p_u

        if not upstream_issue:
            issue_type = "healthy"
        else:
            risky = self.rng.random() < p_p
            issue_type = "risky" if risky else "recoverable"

        score = self.sample_score(issue_type)
        trip = self.should_trip(mode, score, p_p)

        if trip:
            if self.rng.random() < self.p_f:
                return "success", True, issue_type
            return "safe_fail", True, issue_type

        # No trip: request continues down the main path.
        if issue_type == "healthy":
            return "success", False, issue_type

        if issue_type == "recoverable":
            if self.rng.random() < self.recoverable_continue_success:
                return "success", False, issue_type
            return "safe_fail", False, issue_type

        if issue_type == "risky":
            return "catastrophic_fail", False, issue_type

        raise RuntimeError("Unreachable state")

    def run(self, mode: str, p_u: float, p_p: float, runs: int) -> RunResult:
        counts = Counts()

        for _ in range(runs):
            outcome, trip, issue_type = self.simulate_one_request(mode, p_u, p_p)

            if issue_type != "healthy":
                counts.upstream_issues += 1
            if issue_type == "recoverable":
                counts.recoverable_issues += 1
            if issue_type == "risky":
                counts.risky_issues += 1

            if trip:
                counts.trips += 1

            if outcome == "success":
                counts.success += 1
            elif outcome == "safe_fail":
                counts.safe_fail += 1
            elif outcome == "catastrophic_fail":
                counts.catastrophic_fail += 1
            else:
                raise ValueError(f"Unknown outcome: {outcome}")
        success_rate = counts.success / runs
        safe_fail_rate = counts.safe_fail / runs
        catastrophic_fail_rate = counts.catastrophic_fail / runs
        utility = (1.0 * success_rate + 0.0 * safe_fail_rate - 5.0 * catastrophic_fail_rate)

        return RunResult(
            mode=mode,
            p_u=p_u,
            p_p=p_p,
            runs=runs,
            success_rate=counts.success / runs,
            safe_fail_rate=counts.safe_fail / runs,
            catastrophic_fail_rate=counts.catastrophic_fail / runs,
            trip_rate=counts.trips / runs,
            upstream_issue_rate=counts.upstream_issues / runs,
            recoverable_issue_rate=counts.recoverable_issues / runs,
            risky_issue_rate=counts.risky_issues / runs,
            utility = utility #(1.0 * success_rate + 0.0 * safe_fail_rate - 5.0 * catastrophic_fail_rate)
        )


# -----------------------------
# Reporting
# -----------------------------

def print_result_line(result: RunResult) -> None:
    print(
        f"{result.mode:<12} "
        f"p_u={result.p_u:.2f} "
        f"p_p={result.p_p:.2f} "
        f"runs={result.runs:<6d} "
        f"upstream={result.upstream_issue_rate:.4f} "
        f"recoverable={result.recoverable_issue_rate:.4f} "
        f"risky={result.risky_issue_rate:.4f} "
        f"success={result.success_rate:.4f} "
        f"safe_fail={result.safe_fail_rate:.4f} "
        f"cfr={result.catastrophic_fail_rate:.4f} "
        f"trips={result.trip_rate:.4f}"
    )


def print_summary_table(results: List[RunResult]) -> None:
    print("\n=== Summary ===")
    for r in results:
        print_result_line(r)


def write_csv(path: str, results: List[RunResult]) -> None:
    fieldnames = list(asdict(results[0]).keys()) if results else []
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))


# -----------------------------
# CLI
# -----------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate LLM circuit breakers with trip cost.")

    parser.add_argument("--runs", type=int, default=5000, help="Monte Carlo runs per configuration.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")

    parser.add_argument(
        "--p-u",
        type=float,
        default=0.20,
        help="Intrinsic upstream issue probability.",
    )

    parser.add_argument(
        "--p-p-values",
        type=float,
        nargs="+",
        default=[0.10, 0.30, 0.50, 0.70, 0.90],
        help="Propagation probability sweep.",
    )

    # Trip cost / fallback quality
    parser.add_argument(
        "--p-f",
        type=float,
        default=0.65,
        help="Fallback success probability after a trip.",
    )

    parser.add_argument(
        "--recoverable-continue-success",
        type=float,
        default=0.85,
        help="Success probability if a recoverable issue continues without a trip.",
    )

    # Score model
    parser.add_argument("--healthy-score-mean", type=float, default=0.20)
    parser.add_argument("--recoverable-score-mean", type=float, default=0.58)
    parser.add_argument("--risky-score-mean", type=float, default=0.82)
    parser.add_argument("--score-std", type=float, default=0.12)

    # Policy thresholds
    parser.add_argument(
        "--ai-threshold",
        type=float,
        default=0.70,
        help="Fixed threshold for ai_cb.",
    )

    parser.add_argument(
        "--adaptive-base-threshold",
        type=float,
        default=0.72,
        help="Base threshold for adaptive_cb before risk adjustment.",
    )

    parser.add_argument(
        "--adaptive-gamma",
        type=float,
        default=0.22,
        help="How much adaptive_cb lowers its threshold as p_p rises.",
    )

    parser.add_argument(
        "--csv-out",
        type=str,
        default="",
        help="Optional path to write CSV results.",
    )

    return parser.parse_args()


# -----------------------------
# Main
# -----------------------------

def main() -> None:
    args = parse_args()

    sim = CircuitBreakerSimulation(
        seed=args.seed,
        p_f=args.p_f,
        recoverable_continue_success=args.recoverable_continue_success,
        healthy_score_mean=args.healthy_score_mean,
        recoverable_score_mean=args.recoverable_score_mean,
        risky_score_mean=args.risky_score_mean,
        score_std=args.score_std,
        adaptive_base_threshold=args.adaptive_base_threshold,
        adaptive_gamma=args.adaptive_gamma,
        ai_threshold=args.ai_threshold,
    )

    results: List[RunResult] = []
    modes = ["no_cb", "ai_cb", "adaptive_cb"]

    print("=== Running simulation ===")
    print(
        f"runs={args.runs} "
        f"p_u={args.p_u:.2f} "
        f"p_f={args.p_f:.2f} "
        f"recoverable_continue_success={args.recoverable_continue_success:.2f}"
    )
    print(
        f"score_means=(healthy={args.healthy_score_mean:.2f}, "
        f"recoverable={args.recoverable_score_mean:.2f}, "
        f"risky={args.risky_score_mean:.2f}) "
        f"score_std={args.score_std:.2f}"
    )
    print(
        f"thresholds: ai={args.ai_threshold:.2f}, "
        f"adaptive_base={args.adaptive_base_threshold:.2f}, "
        f"adaptive_gamma={args.adaptive_gamma:.2f}"
    )
    print()

    for p_p in args.p_p_values:
        for mode in modes:
            result = sim.run(mode=mode, p_u=args.p_u, p_p=p_p, runs=args.runs)
            results.append(result)
            print_result_line(result)
        print()

    if args.csv_out:
        write_csv(args.csv_out, results)
        print(f"Wrote CSV: {args.csv_out}")

    # Highlight pairwise comparison between ai_cb and adaptive_cb
    print("\n=== ai_cb vs adaptive_cb tradeoff check ===")
    ai_by_pp: Dict[float, RunResult] = {r.p_p: r for r in results if r.mode == "ai_cb"}
    ad_by_pp: Dict[float, RunResult] = {r.p_p: r for r in results if r.mode == "adaptive_cb"}

    for p_p in args.p_p_values:
        ai = ai_by_pp[p_p]
        ad = ad_by_pp[p_p]
        delta_success = ad.success_rate - ai.success_rate
        delta_cfr = ad.catastrophic_fail_rate - ai.catastrophic_fail_rate
        print(
            f"p_p={p_p:.2f} "
            f"adaptive-success-minus-ai={delta_success:+.4f} "
            f"adaptive-cfr-minus-ai={delta_cfr:+.4f}"
        )

    print("\nInterpretation:")
    print("- Negative adaptive-success-minus-ai => adaptive has lower success.")
    print("- Negative adaptive-cfr-minus-ai => adaptive has lower CFR.")
    print("- The desired tradeoff is both values negative at the same p_p.")


if __name__ == "__main__":
    main()
