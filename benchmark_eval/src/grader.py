from __future__ import annotations

import ast
import json
import re
from typing import Tuple

from .schemas import TaskRecord


class SimpleExactMatchGrader:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.last_debug: dict[str, object] | None = None

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        stripped = (text or "").strip()
        match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else stripped

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip())

    @staticmethod
    def _singleton_scalar_value(value: object) -> object | None:
        if not isinstance(value, dict) or len(value) != 1:
            return None
        only_value = next(iter(value.values()))
        if isinstance(only_value, (dict, list)):
            return None
        return only_value

    def _canonicalize(self, text: str) -> tuple[bool, object, str]:
        cleaned = self._strip_code_fences(text)
        try:
            parsed = json.loads(cleaned)
            return True, parsed, json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            pass
        try:
            parsed = ast.literal_eval(cleaned)
            if isinstance(parsed, (dict, list, int, float, bool)):
                return True, parsed, json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except (ValueError, SyntaxError):
            normalized = self._normalize_whitespace(cleaned)
            return False, normalized, normalized
        normalized = self._normalize_whitespace(cleaned)
        return False, normalized, normalized

    def grade(self, task: TaskRecord, final_answer: str) -> Tuple[bool, str]:
        expected_raw = task.reference_answer or ""
        observed_raw = final_answer or ""

        expected_is_json, expected_value, expected_canonical = self._canonicalize(expected_raw)
        observed_is_json, observed_value, observed_canonical = self._canonicalize(observed_raw)

        if expected_is_json and observed_is_json:
            expected_singleton = self._singleton_scalar_value(expected_value)
            observed_singleton = self._singleton_scalar_value(observed_value)
            passed = (
                expected_value == observed_value
                or (expected_singleton is not None and expected_singleton == observed_value)
                or (observed_singleton is not None and expected_value == observed_singleton)
            )
            reason = "json semantic match" if passed else (
                f"json mismatch expected={expected_canonical!r} observed={observed_canonical!r}"
            )
        else:
            passed = expected_canonical == observed_canonical
            reason = "normalized exact match" if passed else (
                f"expected={expected_canonical!r} observed={observed_canonical!r}"
            )

        self.last_debug = {
            "raw_expected": expected_raw,
            "raw_observed": observed_raw,
            "expected_json_parse_succeeded": expected_is_json,
            "observed_json_parse_succeeded": observed_is_json,
            "canonical_expected": expected_canonical,
            "canonical_observed": observed_canonical,
            "passed": passed,
            "reason": reason,
        }

        if self.debug:
            return passed, (
                f"{reason}; "
                f"expected_json={expected_is_json} observed_json={observed_is_json}; "
                f"canonical_expected={expected_canonical!r} canonical_observed={observed_canonical!r}"
            )
        return passed, reason
