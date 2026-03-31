from __future__ import annotations

from abc import ABC, abstractmethod
from models import AgentResult, BreakerDecision


class CircuitBreaker(ABC):
    def __init__(self) -> None:
        self.state = "CLOSED"
        self.trip_count = 0

    @abstractmethod
    def before_call(self) -> BreakerDecision:
        raise NotImplementedError

    @abstractmethod
    def after_call(self, result: AgentResult, chain_length: int) -> BreakerDecision:
        raise NotImplementedError
