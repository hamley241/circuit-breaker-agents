from __future__ import annotations

from typing import Any, Dict
from injections.base import Injection


class ContextOverloadInjection(Injection):
    name = "context_overload"

    def apply(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        artifact = dict(artifact)
        distractor = " ".join(["irrelevant_context"] * 500)
        artifact["distractor_blob"] = distractor
        artifact["context_overload"] = True
        return artifact
