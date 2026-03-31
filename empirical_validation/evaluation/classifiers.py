from __future__ import annotations

from typing import Any, Dict


def detect_upstream_failure(planner_output: Dict[str, Any], executor_output: Dict[str, Any]) -> bool:
    if planner_output.get("corrupted") or planner_output.get("contradictory_injected"):
        return True
    if not planner_output.get("plan_steps"):
        return True
    if executor_output.get("confidence", 1.0) < 0.5:
        return True
    return False


def final_success(verifier_output: Dict[str, Any], executor_output: Dict[str, Any], reference_answer: str) -> bool:
    if verifier_output.get("verdict") == "pass":
        return True
    answer = str(executor_output.get("answer", "")).strip().lower()
    return reference_answer.strip().lower() in answer


def detect_cascade(upstream_failed: bool, final_success_value: bool, breaker_blocked_downstream: bool) -> bool:
    return upstream_failed and (not breaker_blocked_downstream) and (not final_success_value)
