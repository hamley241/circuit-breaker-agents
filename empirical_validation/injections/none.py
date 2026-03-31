from __future__ import annotations

from typing import Any, Dict
from injections.base import Injection


class NoInjection(Injection):
    name = "none"

    def apply(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        return artifact
