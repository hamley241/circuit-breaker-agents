from __future__ import annotations

from dataclasses import dataclass

from .config import BreakerConfig
from .schemas import CheckerResult


@dataclass
class StaticBreaker:
    config: BreakerConfig

    def should_trip(self, checker: CheckerResult) -> bool:
        return (not checker.valid) or (checker.confidence < self.config.static_threshold)


@dataclass
class AdaptiveBreaker:
    config: BreakerConfig

    def threshold_for(self, prior_failures: int, rolling_risk: float) -> float:
        tau = (
            self.config.adaptive_base_threshold
            + self.config.adaptive_prior_failure_weight * min(prior_failures, 2)
            + self.config.adaptive_rolling_risk_weight * min(rolling_risk, 1.0)
        )
        return min(tau, self.config.adaptive_max_threshold)

    def should_trip(self, checker: CheckerResult, prior_failures: int, rolling_risk: float) -> bool:
        threshold = self.threshold_for(prior_failures=prior_failures, rolling_risk=rolling_risk)
        return (not checker.valid) or (checker.confidence < threshold)
