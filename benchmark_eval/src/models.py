from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict

from .config import ModelConfig

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


@dataclass
class ModelResponse:
    text: str


class BaseModelClient:
    def generate(self, prompt: str, context: Dict[str, Any]) -> ModelResponse:
        raise NotImplementedError


class StubModelClient(BaseModelClient):
    """A deterministic stub so the scaffold runs without external APIs."""

    def generate(self, prompt: str, context: Dict[str, Any]) -> ModelResponse:
        task = context.get('task', {})
        reference = str(task.get('reference_answer', ''))
        stage = context.get('stage', 'unknown')
        fallback = bool(context.get('fallback', False))

        if stage == 'planner':
            text = json.dumps({
                'plan': ['answer the task', 'verify against benchmark grading expectations'],
                'assumptions': [] if not fallback else ['fallback planner used'],
            })
        elif stage == 'executor':
            text = json.dumps({
                'candidate_answer': reference,
                'evidence': ['stub execution'],
                'notes': [f'stage={stage}', f'fallback={fallback}'],
            })
        elif stage == 'verifier':
            text = json.dumps({
                'final_answer': reference,
                'verdict': 'accept',
                'issues': [] if not fallback else ['fallback verifier used'],
            })
        elif stage == 'checker':
            text = json.dumps({
                'valid': True,
                'confidence': 0.9,
                'reasons': ['stub checker accepted output'],
            })
        else:
            text = '{}'
        return ModelResponse(text=text)


class OpenAIResponsesClient(BaseModelClient):
    def __init__(self, config: ModelConfig):
        if OpenAI is None:
            raise RuntimeError('openai package is not installed. Run: pip install -r requirements.txt')
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise RuntimeError(
                f'Missing API key. Set {config.api_key_env} in your shell or .env before running.'
            )
        self.client = OpenAI(api_key=api_key, timeout=config.timeout_seconds)
        self.model_name = config.model_name
        self.max_output_tokens = config.max_output_tokens

    def generate(self, prompt: str, context: Dict[str, Any]) -> ModelResponse:
        payload = json.dumps(context, ensure_ascii=False, indent=2)
        response = self.client.responses.create(
            model=self.model_name,
            instructions=prompt,
            input=payload,
            max_output_tokens=self.max_output_tokens,
        )
        text = getattr(response, 'output_text', '') or ''
        if not text:
            raise RuntimeError('OpenAI response did not contain output_text.')
        return ModelResponse(text=text)


def build_model_client(config: ModelConfig) -> BaseModelClient:
    provider = config.provider.lower()
    if provider == 'stub':
        return StubModelClient()
    if provider == 'openai':
        return OpenAIResponsesClient(config)
    raise ValueError(f'Unsupported MODEL_PROVIDER: {config.provider}')
