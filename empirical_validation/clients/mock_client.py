from __future__ import annotations

import json
import random
from clients.base import LLMClient


class MockLLMClient(LLMClient):
    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def generate(self, prompt: str) -> str:
        confidence = round(self.rng.uniform(0.7, 0.95), 2)

        if "You are PlannerAgent" in prompt:
            payload = {
                "plan_steps": [
                    "Read the question",
                    "Identify the key fact needed",
                    "Return the answer clearly",
                ],
                "extracted_facts": ["mock_fact_1", "mock_fact_2"],
                "confidence": confidence,
            }
            return json.dumps(payload)

        if "You are ExecutorAgent" in prompt:
            ref = self._extract_field(prompt, "Reference answer:")
            payload = {
                "answer": ref or "mock answer",
                "reasoning_summary": "Used planner output successfully.",
                "confidence": confidence,
            }
            return json.dumps(payload)

        if "You are VerifierAgent" in prompt:
            payload = {
                "verdict": "pass",
                "failure_type": None,
                "confidence": confidence,
                "notes": "Mock verifier accepted the executor output.",
            }
            return json.dumps(payload)

        return json.dumps({
            "content": "fallback mock response",
            "confidence": confidence,
            "notes": "fallback",
        })

    def _extract_field(self, prompt: str, prefix: str) -> str:
        for line in prompt.splitlines():
            if line.strip().startswith(prefix):
                return line.split(prefix, 1)[1].strip()
        return "unknown"
