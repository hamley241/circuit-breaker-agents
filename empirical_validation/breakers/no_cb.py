from __future__ import annotations

from breakers.base import CircuitBreaker
from models import AgentResult, BreakerDecision


class NoCircuitBreaker(CircuitBreaker):
    def before_call(self) -> BreakerDecision:
        return BreakerDecision(True, self.state, self.state, False, None)

    def after_call(self, result: AgentResult, chain_length: int) -> BreakerDecision:
        return BreakerDecision(True, self.state, self.state, False, None)
