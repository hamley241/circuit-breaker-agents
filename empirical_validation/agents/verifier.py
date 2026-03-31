from __future__ import annotations

from typing import Any, Dict

from agents.base import Agent
from agents.common import parse_json_or_fallback
from models import AgentResult


class VerifierAgent(Agent):
    def run(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        executor_output = context.get("executor_output", {})

        # Deterministic failure checks before calling the model.
        if executor_output.get("execution_error"):
            parsed = {
                "verdict": "fail",
                "failure_type": executor_output.get("execution_error"),
                "confidence": 0.95,
                "notes": "Executor output indicates upstream or execution failure.",
            }
            return AgentResult(
                agent_name="verifier",
                raw_text=str(parsed),
                parsed=parsed,
                success=False,
                confidence_signal=0.95,
                failure_reason=executor_output.get("execution_error"),
            )

        answer = executor_output.get("answer", "")
        if not isinstance(answer, str) or answer.strip() == "":
            parsed = {
                "verdict": "fail",
                "failure_type": "empty_answer",
                "confidence": 0.95,
                "notes": "Executor produced an empty answer.",
            }
            return AgentResult(
                agent_name="verifier",
                raw_text=str(parsed),
                parsed=parsed,
                success=False,
                confidence_signal=0.95,
                failure_reason="empty_answer",
            )

        prompt = f'''
You are VerifierAgent.
Check whether the answer matches the reference answer.
Return strict JSON with keys:
- verdict: one of ["pass", "fail"]
- failure_type: short string or null
- confidence: float between 0 and 1
- notes: string

Question: {task['question']}
Reference answer: {task['reference_answer']}
Executor output: {executor_output}
'''
        raw = self.client.generate(prompt)
        parsed, conf, success, failure_reason = parse_json_or_fallback(raw)

        # Normalize verifier outputs
        verdict = parsed.get("verdict")
        if verdict not in {"pass", "fail"}:
            parsed["verdict"] = "fail"
            parsed["failure_type"] = "invalid_verifier_output"
            parsed["notes"] = "Verifier output missing valid verdict."
            success = False
            failure_reason = "invalid_verifier_output"

        return AgentResult(
            agent_name="verifier",
            raw_text=raw,
            parsed=parsed,
            success=success,
            confidence_signal=conf,
            failure_reason=failure_reason,
        )
