from __future__ import annotations

from typing import Any, Dict
from injections.base import Injection


class EmptyToolResultInjection(Injection):
    name = "empty_tool_result"

    def apply(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        artifact = dict(artifact)
        artifact["tool_result"] = ""
        artifact["tool_empty"] = True
        return artifact
