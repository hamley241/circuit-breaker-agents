from __future__ import annotations

import json
from pathlib import Path


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def dumps_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
