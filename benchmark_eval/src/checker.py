from __future__ import annotations

import json
from typing import Any, Dict, List

from .config import PROMPTS_DIR
from .models import BaseModelClient
from .schemas import CheckerResult
from .utils import load_text


class Checker:
    def __init__(self, model: BaseModelClient):
        self.model = model
        self.prompt = load_text(PROMPTS_DIR / 'checker.txt')

    def check(self, stage: str, output_text: str, task: Dict[str, Any]) -> CheckerResult:
        stripped = (output_text or '').strip()
        if not stripped:
            return CheckerResult(valid=False, confidence=0.0, reasons=['empty output'])

        try:
            json.loads(stripped)
        except Exception:
            return CheckerResult(valid=False, confidence=0.05, reasons=['non-JSON output'])

        response = self.model.generate(
            prompt=self.prompt,
            context={'stage': stage, 'task': task, 'candidate_output': output_text},
        )
        try:
            parsed = json.loads(response.text)
            return CheckerResult.model_validate(parsed)
        except Exception:
            return CheckerResult(valid=False, confidence=0.0, reasons=['checker returned invalid JSON'])

    @staticmethod
    def _coerce_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {'true', 'yes', '1', 'trip'}
        return bool(value)

    @staticmethod
    def _clamp_score(value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, score))

    @staticmethod
    def _as_str_list(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    @staticmethod
    def _used_additional_context(reasoning: str) -> bool:
        lowered = reasoning.lower()
        return any(token in lowered for token in ('task', 'question', 'requirement', 'downstream', 'stage'))

    def evaluate_v2_verifier(
        self,
        verifier_name: str,
        verifier_variant: str,
        payload: Dict[str, Any],
    ) -> tuple[bool, CheckerResult]:
        prompt = (
            "You are an observer-mode verifier for a multi-stage agent benchmark.\n"
            "Recommend whether a circuit breaker should trip, but do not execute or modify the trajectory.\n"
            "Use only the provided observer payload.\n"
            "Return strict JSON only with this schema:\n"
            "{\n"
            "  \"predicted_trip\": true,\n"
            "  \"predicted_trip_reason\": \"...\",\n"
            "  \"verifier_reasoning\": \"...\"\n"
            "}\n"
        )
        response = self.model.generate(
            prompt=prompt,
            context={
                'stage': 'v2_observer_verifier',
                'verifier_name': verifier_name,
                'verifier_variant': verifier_variant,
                'payload': payload,
            },
        )
        try:
            parsed = json.loads(response.text)
        except Exception:
            reasoning = 'observer verifier returned invalid JSON'
            return False, CheckerResult(
                valid=True,
                confidence=0.0,
                reasons=[reasoning],
                verifier_name=verifier_name,
                verifier_variant=verifier_variant,
                verifier_reasoning=reasoning,
                verifier_used_additional_context=False,
            )

        predicted_trip = self._coerce_bool(parsed.get('predicted_trip', False))
        reason = str(parsed.get('predicted_trip_reason', '')).strip()
        reasoning = str(parsed.get('verifier_reasoning', reason)).strip()
        return predicted_trip, CheckerResult(
            valid=True,
            confidence=1.0,
            reasons=[reason] if reason else [],
            verifier_name=verifier_name,
            verifier_variant=verifier_variant,
            verifier_reasoning=reasoning,
            verifier_used_additional_context=self._used_additional_context(reasoning),
        )

    def compute_recoverability(
        self,
        representation_name: str,
        representation: Any,
        task_question: str,
    ) -> CheckerResult:
        prompt = (
            "You are evaluating recoverability of an intermediate representation.\n"
            "What information needed for the final answer is missing from this representation?\n"
            "Return strict JSON only with this schema:\n"
            "{\n"
            "  \"recoverability_score\": 0.0,\n"
            "  \"recoverability_missing_fields\": [\"...\"],\n"
            "  \"verifier_reasoning\": \"...\"\n"
            "}\n"
            "Use 1.0 when the representation appears sufficient for reconstructing the final answer, "
            "and 0.0 when it appears unusable.\n"
        )
        response = self.model.generate(
            prompt=prompt,
            context={
                'stage': 'v2_recoverability',
                'representation_name': representation_name,
                'task_question': task_question,
                'representation': representation,
            },
        )
        try:
            parsed = json.loads(response.text)
        except Exception:
            parsed = {}
        score = self._clamp_score(parsed.get('recoverability_score', 0.0))
        missing_fields = self._as_str_list(parsed.get('recoverability_missing_fields'))
        reasoning = str(parsed.get('verifier_reasoning', '')).strip()
        return CheckerResult(
            valid=True,
            confidence=score,
            reasons=missing_fields,
            recoverability_score=score,
            recoverability_missing_fields=missing_fields,
            recoverability_raw_response=response.text,
            verifier_reasoning=reasoning,
        )
