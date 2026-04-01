#!/usr/bin/env python3
"""
simulate_circuit_breakers.py

LLM circuit breaker simulation with:
- intrinsic failure probability: p_u
- propagation probability: p_p
- imperfect fallback success after trip: p_f
- configurable fallback degradation under load
- configurable catastrophe penalty in utility

Degradation modes:
- none:
    p_f_eff = p_f
- linear_subtractive:
    p_f_eff = p_f - alpha * p_p
- linear_multiplicative:
    p_f_eff = p_f * (1 - alpha * p_p)
- exp:
    p_f_eff = p_f * exp(-alpha * p_p)

Utility:
    success = +1
    safe_fail = 0
    catastrophic_fail = -catastrophe_cost
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple


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
    catastrophe_cost: float
    fallback_degradation_mode: str
    fallback_degradation_alpha: float
    base_p_f: float


@dataclass
class Counts:
    success: int = 0
    safe_fail: int = 0
    catastrophic_fail: int = 0
    trips: int = 0
    upstream_issues: int = 0
    recoverable_issues: int = 0
    risky_issues: int = 0


class CircuitBreakerSimulation:
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
        fallback_degradation_alpha: float,
        fallback_degradation_mode: str,
        catastrophe_cost: float,
    ) -> None:
        self.rng = random.Random(seed)

        self.p_f = p_f
        self.fallback_degradation_alpha = fallback_degradation_alpha
        self.fallback_degradation_mode = fallback_degradation_mode
        self.catastrophe_cost = catastrophe_cost
        self.recoverable_continue_success = recoverable_continue_success

        self.healthy_score_mean = healthy_score_mean
        self.recoverable_score_mean = recoverable_score_mean
        self.risky_score_mean = risky_score_mean
        self.score_std = score_std

        self.ai_policy = Policy(name="ai_cb", threshold=ai_threshold)
        self.adaptive_policy = Policy(
            name="adaptive_cb",
            threshold=adaptive_base_threshold,
            base_threshold=adaptive_base_threshold,
            adapt_gamma=adaptive_gamma,
        )
        self.no_cb_policy = Policy(name="no_cb", threshold=float("inf"))

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
        assert self.adaptive_policy.base_threshold is not None
        threshold = self.adaptive_policy.base_threshold - self.adaptive_policy.adapt_gamma * p_p
        return max(0.0, min(1.0, threshold))

    def get_effective_fallback_success(self, p_p: float) -> float:
        alpha = self.fallback_degradation_alpha
        mode = self.fallback_degradation_mode
        base = self.p_f

        if mode == "none":
            eff = base
        elif mode == "linear_subtractive":
            eff = base - alpha * p_p
        elif mode == "linear_multiplicative":
            eff = base * (1.0 - alpha * p_p)
        elif mode == "exp":
            eff = base * math.exp(-alpha * p_p)
        else:
            raise ValueError(f"Unknown fallback_degradation_mode: {mode}")

        return max(0.0, min(1.0, eff))

    def should_trip(self, mode: str, score: float, p_p: float) -> bool:
        if mode == "no_cb":
            return False
        if mode == "ai_cb":
            return score >= self.ai_policy.threshold
        if mode == "adaptive_cb":
            return score >= self.get_adaptive_threshold(p_p)
        raise ValueError(f"Unknown mode: {mode}")

    def simulate_one_request(self, mode: str, p_u: float, p_p: float) -> Tuple[str, bool, str]:
        upstream_issue = self.rng.random() < p_u

        if not upstream_issue:
            issue_type = "healthy"
        else:
            risky = self.rng.random() < p_p
            issue_type = "risky" if risky else "recoverable"

        score = self.sample_score(issue_type)
        trip = self.should_trip(mode, score, p_p)

        if trip:
            effective_p_f = self.get_effective_fallback_success(p_p)
            if self.rng.random() < effective_p_f:
                return "success", True, issue_type
            return "safe_fail", True, issue_type

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
        trip_rate = counts.trips / runs
        upstream_issue_rate = counts.upstream_issues / runs
        recoverable_issue_rate = counts.recoverable_issues / runs
        risky_issue_rate = counts.risky_issues / runs

        utility = success_rate - self.catastrophe_cost * catastrophic_fail_rate

        return RunResult(
            mode=mode,
            p_u=p_u,
            p_p=p_p,
            runs=runs,
            success_rate=success_rate,
            safe_fail_rate=safe_fail_rate,
            catastrophic_fail_rate=catastrophic_fail_rate,
            trip_rate=trip_rate,
            upstream_issue_rate=upstream_issue_rate,
            recoverable_issue_rate=recoverable_issue_rate,
            risky_issue_rate=risky_issue_rate,
            utility=utility,
            catastrophe_cost=self.catastrophe_cost,
            fallback_degradation_mode=self.fallback_degradation_mode,
            fallback_degradation_alpha=self.fallback_degradation_alpha,
            base_p_f=self.p_f,
        )


def print_result_line(result: RunResult) -> None:
    print(
        f"{result.mode:<12} "
        f"p_u={result.p_u:.2f} "
        f"p_p={result.p_p:.2f} "
        f"runs={result.runs:<6d} "
        f"success={result.success_rate:.4f} "
        f"safe_fail={result.safe_fail_rate:.4f} "
        f"cfr={result.catastrophic_fail_rate:.4f} "
        f"trips={result.trip_rate:.4f} "
        f"utility={result.utility:.4f}"
    )


def write_csv(path: str, results: List[RunResult]) -> None:
    if not results:
        return
    fieldnames = list(asdict(results[0]).keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate LLM circuit breakers.")

    parser.add_argument("--runs", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument("--p-u", type=float, default=0.20)
    parser.add_argument(
        "--p-p-values",
        type=float,
        nargs="+",
        default=[0.10, 0.30, 0.50, 0.70, 0.90],
    )

    parser.add_argument("--p-f", type=float, default=0.70)
    parser.add_argument(
        "--fallback-degradation-alpha",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--fallback-degradation-mode",
        type=str,
        default="none",
        choices=["none", "linear_subtractive", "linear_multiplicative", "exp"],
    )

    parser.add_argument("--catastrophe-cost", type=float, default=5.0)
    parser.add_argument("--recoverable-continue-success", type=float, default=0.85)

    parser.add_argument("--healthy-score-mean", type=float, default=0.20)
    parser.add_argument("--recoverable-score-mean", type=float, default=0.58)
    parser.add_argument("--risky-score-mean", type=float, default=0.82)
    parser.add_argument("--score-std", type=float, default=0.12)

    parser.add_argument("--ai-threshold", type=float, default=0.70)
    parser.add_argument("--adaptive-base-threshold", type=float, default=0.72)
    parser.add_argument("--adaptive-gamma", type=float, default=0.22)

    parser.add_argument("--csv-out", type=str, default="")

    return parser.parse_args()


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
        fallback_degradation_alpha=args.fallback_degradation_alpha,
        fallback_degradation_mode=args.fallback_degradation_mode,
        catastrophe_cost=args.catastrophe_cost,
    )

    results: List[RunResult] = []
    modes = ["no_cb", "ai_cb", "adaptive_cb"]

    print("=== Running simulation ===")
    print(
        f"runs={args.runs} "
        f"p_u={args.p_u:.2f} "
        f"p_f={args.p_f:.2f} "
        f"degradation_mode={args.fallback_degradation_mode} "
        f"degradation_alpha={args.fallback_degradation_alpha:.2f} "
        f"catastrophe_cost={args.catastrophe_cost:.2f}"
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

    print("\n=== ai_cb vs adaptive_cb tradeoff check ===")
    ai_by_pp: Dict[float, RunResult] = {r.p_p: r for r in results if r.mode == "ai_cb"}
    ad_by_pp: Dict[float, RunResult] = {r.p_p: r for r in results if r.mode == "adaptive_cb"}

    for p_p in args.p_p_values:
        ai = ai_by_pp[p_p]
        ad = ad_by_pp[p_p]
        delta_success = ad.success_rate - ai.success_rate
        delta_cfr = ad.catastrophic_fail_rate - ai.catastrophic_fail_rate
        delta_utility = ad.utility - ai.utility
        print(
            f"p_p={p_p:.2f} "
            f"adaptive-success-minus-ai={delta_success:+.4f} "
            f"adaptive-cfr-minus-ai={delta_cfr:+.4f} "
            f"adaptive-utility-minus-ai={delta_utility:+.4f}"
        )

    print("\nInterpretation:")
    print("- Negative success delta => adaptive has lower success.")
    print("- Negative CFR delta => adaptive has lower CFR.")
    print("- Positive utility delta => adaptive has higher utility.")


if __name__ == "__main__":
    main()
