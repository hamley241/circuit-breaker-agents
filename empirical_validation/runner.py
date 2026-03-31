from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import random
import uuid
from typing import Any, Dict, List

from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.verifier import VerifierAgent
from breakers.no_cb import NoCircuitBreaker
from breakers.ai_cb import AICircuitBreaker
from breakers.adaptive_cb import AdaptiveCircuitBreaker
from evaluation.classifiers import detect_upstream_failure, final_success, detect_cascade
from models import RunRecord
from injections.none import NoInjection
from injections.corrupt_json import CorruptJSONInjection
from injections.contradictory_fact import ContradictoryFactInjection
from injections.context_overload import ContextOverloadInjection
from injections.empty_tool_result import EmptyToolResultInjection


def load_tasks(path: Path) -> List[Dict[str, Any]]:
    tasks = []
    with path.open() as f:
        for line in f:
            tasks.append(json.loads(line))
    return tasks


def make_breaker(cb_type: str):
    if cb_type == "no_cb":
        return NoCircuitBreaker()
    if cb_type == "ai_cb":
        return AICircuitBreaker()
    if cb_type == "adaptive_cb":
        return AdaptiveCircuitBreaker()
    raise ValueError(f"Unknown cb_type: {cb_type}")


def make_injection(name: str):
    mapping = {
        "none": NoInjection(),
        "corrupt_json": CorruptJSONInjection(),
        "contradictory_fact": ContradictoryFactInjection(),
        "context_overload": ContextOverloadInjection(),
        "empty_tool_result": EmptyToolResultInjection(),
    }
    if name not in mapping:
        raise ValueError(f"Unknown injection: {name}")
    return mapping[name]


def run_experiment(
    client,
    provider: str,
    model: str,
    dataset_path: Path,
    runs: int,
    cb_type: str,
    injection_name: str,
    inject_rate: float,
    output_jsonl: Path,
    seed: int = 42,
) -> None:
    rng = random.Random(seed)
    tasks = load_tasks(dataset_path)
    planner = PlannerAgent(client)
    executor = ExecutorAgent(client)
    verifier = VerifierAgent(client)

    # ✅ CREATE INJECTION ONCE
    injection = make_injection(injection_name)

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w") as out:
        for i in range(runs):
            task = tasks[i % len(tasks)]
            breaker = make_breaker(cb_type)
            injection_applied = rng.random() < inject_rate and injection_name != "none"
            run_id = str(uuid.uuid4())

            # Planner
            pre = breaker.before_call()
            if not pre.allow:
                planner_output = {"blocked": True}
                executor_output = {"blocked": True}
                verifier_output = {"verdict": "fail", "failure_type": "blocked_before_planner"}
                upstream_failed = True
                final_ok = False
                cascade = False
            else:
                planner_res = planner.run(task, {})
                breaker.after_call(planner_res, chain_length=3)
                planner_output = dict(planner_res.parsed)
                if injection_applied:
                    planner_output = injection.apply(planner_output)

                # Executor
                pre = breaker.before_call()
                breaker_blocked_downstream = not pre.allow
                if breaker_blocked_downstream:
                    executor_output = {"blocked": True}
                    verifier_output = {"verdict": "fail", "failure_type": "blocked_before_executor"}
                else:
                    executor_res = executor.run(task, {"planner_output": planner_output})
                    breaker.after_call(executor_res, chain_length=3)
                    executor_output = dict(executor_res.parsed)

                    # Verifier
                    pre = breaker.before_call()
                    breaker_blocked_downstream = breaker_blocked_downstream or (not pre.allow)
                    if not pre.allow:
                        verifier_output = {"verdict": "fail", "failure_type": "blocked_before_verifier"}
                    else:
                        verifier_res = verifier.run(task, {"executor_output": executor_output})
                        breaker.after_call(verifier_res, chain_length=3)
                        verifier_output = dict(verifier_res.parsed)

                upstream_failed = detect_upstream_failure(planner_output, executor_output)
                final_ok = final_success(verifier_output, executor_output, task["reference_answer"])
                cascade = detect_cascade(upstream_failed, final_ok, breaker_blocked_downstream)

            record = RunRecord(
                run_id=run_id,
                task_id=task["task_id"],
                provider=provider,
                model=model,
                cb_type=cb_type,
                injection=injection_name,
                inject_rate=inject_rate,
                injection_applied=injection_applied,
                upstream_failure=upstream_failed,
                cascade=cascade,
                final_success=final_ok,
                breaker_trip_count=breaker.trip_count,
                planner=planner_output,
                executor=executor_output,
                verifier=verifier_output,
                metadata={"seed": seed, "run_index": i},
            )
            out.write(json.dumps(record.to_dict()) + "\n")
