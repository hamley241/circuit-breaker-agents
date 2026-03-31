from __future__ import annotations

from breakers.base import CircuitBreaker
from models import AgentResult, BreakerDecision


class AdaptiveCircuitBreaker(CircuitBreaker):
    def __init__(self, base_threshold: float = 0.7) -> None:
        super().__init__()
        self.base_threshold = base_threshold
        self.failure_count = 0

    def before_call(self) -> BreakerDecision:
        allow = self.state != "OPEN"
        return BreakerDecision(allow, self.state, self.state, False, "open" if not allow else None)

    def after_call(self, result: AgentResult, chain_length: int) -> BreakerDecision:
        state_before = self.state
        dynamic_threshold = max(0.5, self.base_threshold - 0.05 * max(0, chain_length - 2))
        semantic_failure = (not result.success) or (result.confidence_signal < dynamic_threshold)
        if chain_length >= 3 and result.confidence_signal < dynamic_threshold + 0.05:
            semantic_failure = True
        if semantic_failure:
            self.failure_count += 1
        else:
            self.failure_count = max(0, self.failure_count - 1)
        if self.failure_count >= 1:
            self.state = "OPEN"
            self.trip_count += 1
        return BreakerDecision(
            allow=self.state != "OPEN",
            state_before=state_before,
            state_after=self.state,
            tripped=self.state == "OPEN" and state_before != "OPEN",
            reason=f"adaptive_threshold={dynamic_threshold:.2f}" if semantic_failure else None,
        )
