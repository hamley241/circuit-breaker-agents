from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Injection(ABC):
    name: str = "base"

    @abstractmethod
    def apply(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
