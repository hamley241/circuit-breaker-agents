from __future__ import annotations

from typing import Any, Dict

from agents.base import Agent
from agents.common import parse_json_or_fallback
from models import AgentResult


class PlannerAgent(Agent):
    def run(self, task: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        prompt = f'''
You are PlannerAgent.
Return strict JSON with keys:
- plan_steps: list[str]
- extracted_facts: list[str]
- confidence: float between 0 and 1

Task:
Question: {task['question']}
Reference answer: {task['reference_answer']}
'''
        raw = self.client.generate(prompt)
        parsed, conf, success, failure_reason = parse_json_or_fallback(raw)
        return AgentResult(
            agent_name="planner",
            raw_text=raw,
            parsed=parsed,
            success=success,
            confidence_signal=conf,
            failure_reason=failure_reason,
        )
