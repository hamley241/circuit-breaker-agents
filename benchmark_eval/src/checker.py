from __future__ import annotations

import json
from typing import Any, Dict

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
