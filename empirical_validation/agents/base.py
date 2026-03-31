from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from clients.base import LLMClient
from models import AgentResult


class Agent(ABC):
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    @abstractmethod
    def run(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        raise NotImplementedError
