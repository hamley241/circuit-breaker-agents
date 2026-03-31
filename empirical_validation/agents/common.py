from __future__ import annotations

import json
from typing import Any, Dict, Tuple


def parse_json_or_fallback(text: str) -> Tuple[Dict[str, Any], float, bool, str | None]:
    try:
        parsed = json.loads(text)
        confidence = float(parsed.get("confidence", 0.6))
        return parsed, confidence, True, None
    except Exception:
        return {"content": text, "confidence": 0.4}, 0.4, False, "malformed_json"
