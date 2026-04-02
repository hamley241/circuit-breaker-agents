from __future__ import annotations

from typing import Tuple

from .schemas import TaskRecord


class SimpleExactMatchGrader:
    def grade(self, task: TaskRecord, final_answer: str) -> Tuple[bool, str]:
        expected = task.reference_answer.strip()
        observed = (final_answer or "").strip()
        if observed == expected:
            return True, "exact match"
        return False, f"expected={expected!r} observed={observed!r}"
