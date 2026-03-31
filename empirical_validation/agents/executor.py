from __future__ import annotations

from typing import Any, Dict

from agents.base import Agent
from agents.common import parse_json_or_fallback
from models import AgentResult


class ExecutorAgent(Agent):
    def run(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        planner_output = context.get("planner_output", {})

        # Hard dependency on planner structure.
        # If the upstream artifact is malformed, degrade explicitly.
        plan_steps = planner_output.get("plan_steps")
        if not isinstance(plan_steps, list) or len(plan_steps) == 0:
            parsed = {
                "answer": "",
                "reasoning_summary": "Planner output invalid or missing required field 'plan_steps'.",
                "confidence": 0.2,
                "execution_error": "invalid_planner_output",
            }
            return AgentResult(
                agent_name="executor",
                raw_text=str(parsed),
                parsed=parsed,
                success=False,
                confidence_signal=0.2,
                failure_reason="invalid_planner_output",
            )

        prompt = f'''
You are ExecutorAgent.
Use the planner output to answer the question.
Return strict JSON with keys:
- answer: string
- reasoning_summary: string
- confidence: float between 0 and 1

Question: {task['question']}
Planner output: {planner_output}
'''
        raw = self.client.generate(prompt)
        parsed, conf, success, failure_reason = parse_json_or_fallback(raw)

        # Additional guardrail: if the model returns malformed executor output,
        # normalize it into a failure state.
        if not isinstance(parsed.get("answer"), str) or parsed.get("answer", "").strip() == "":
            parsed["execution_error"] = "empty_or_missing_answer"
            return AgentResult(
                agent_name="executor",
                raw_text=raw,
                parsed=parsed,
                success=False,
                confidence_signal=conf,
                failure_reason="empty_or_missing_answer",
            )

        return AgentResult(
            agent_name="executor",
            raw_text=raw,
            parsed=parsed,
            success=success,
            confidence_signal=conf,
            failure_reason=failure_reason,
        )
