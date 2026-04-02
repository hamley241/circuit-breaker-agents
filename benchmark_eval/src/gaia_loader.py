from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .schemas import TaskRecord


def load_tasks(path: Path) -> List[TaskRecord]:
    records: List[TaskRecord] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(TaskRecord.model_validate(json.loads(line)))
    return records
