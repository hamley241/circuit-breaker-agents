from __future__ import annotations

from breakers.base import CircuitBreaker
from models import AgentResult, BreakerDecision


class AICircuitBreaker(CircuitBreaker):
    def __init__(self, confidence_threshold: float = 0.65, failure_threshold: int = 1) -> None:
        super().__init__()
        self.confidence_threshold = confidence_threshold
        self.failure_threshold = failure_threshold
        self.failure_count = 0

    def before_call(self) -> BreakerDecision:
        allow = self.state != "OPEN"
        return BreakerDecision(allow, self.state, self.state, False, "open" if not allow else None)

    def after_call(self, result: AgentResult, chain_length: int) -> BreakerDecision:
        state_before = self.state
        semantic_failure = (not result.success) or (result.confidence_signal < self.confidence_threshold)
        if semantic_failure:
            self.failure_count += 1
        else:
            self.failure_count = 0
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.trip_count += 1
        return BreakerDecision(
            allow=self.state != "OPEN",
            state_before=state_before,
            state_after=self.state,
            tripped=self.state == "OPEN" and state_before != "OPEN",
            reason="low_confidence_or_failure" if semantic_failure else None,
        )
