from __future__ import annotations

import json
from typing import Any, Dict

from .breaker import AdaptiveBreaker, StaticBreaker
from .checker import Checker
from .config import BreakerConfig, PROMPTS_DIR
from .models import BaseModelClient
from .schemas import CheckerResult, RunTrace, StageTrace, TaskRecord
from .utils import load_text


class BenchmarkAgentRunner:
    def __init__(self, model: BaseModelClient, breaker_config: BreakerConfig | None = None):
        self.model = model
        self.checker = Checker(model)
        self.static_breaker = StaticBreaker(breaker_config or BreakerConfig())
        self.adaptive_breaker = AdaptiveBreaker(breaker_config or BreakerConfig())

    def _prompt_for(self, stage: str, fallback: bool) -> str:
        filename = f"fallback_{stage}.txt" if fallback else f"{stage}.txt"
        return load_text(PROMPTS_DIR / filename)

    def _run_stage(self, stage: str, task: TaskRecord, payload: Dict[str, Any], fallback: bool) -> str:
        response = self.model.generate(
            prompt=self._prompt_for(stage, fallback=fallback),
            context={
                'stage': stage,
                'task': task.model_dump(),
                'payload': payload,
                'fallback': fallback,
            },
        )
        return response.text

    def _record_stage(
        self,
        trace: RunTrace,
        stage: str,
        raw_output: str,
        checker: CheckerResult,
        breaker_tripped: bool,
        used_fallback: bool,
    ) -> None:
        trace.stages.append(
            StageTrace(
                stage=stage,
                raw_output=raw_output,
                checker=checker,
                breaker_tripped=breaker_tripped,
                used_fallback=used_fallback,
            )
        )
        if not checker.valid:
            trace.upstream_failure_seen = True

    def _should_trip(self, policy: str, checker: CheckerResult, prior_failures: int, rolling_risk: float) -> bool:
        if policy == 'no_cb':
            return False
        if policy == 'ai_cb':
            return self.static_breaker.should_trip(checker)
        if policy == 'adaptive_cb':
            return self.adaptive_breaker.should_trip(checker, prior_failures=prior_failures, rolling_risk=rolling_risk)
        raise ValueError(f'Unknown policy: {policy}')

    @staticmethod
    def _safe_json_loads(raw_text: str, default: Dict[str, Any]) -> Dict[str, Any]:
        try:
            parsed = json.loads(raw_text)
            return parsed if isinstance(parsed, dict) else default
        except Exception:
            return default

    def execute_task(self, task: TaskRecord, policy: str, rolling_risk: float = 0.0) -> RunTrace:
        trace = RunTrace(task_id=task.task_id, policy=policy)
        prior_failures = 0

        planner_output = self._run_stage('planner', task, payload={'question': task.question}, fallback=False)
        planner_check = self.checker.check('planner', planner_output, task.model_dump())
        planner_trip = self._should_trip(policy, planner_check, prior_failures, rolling_risk)
        if planner_trip:
            trace.trip_count += 1
            fallback_output = self._run_stage('planner', task, payload={'question': task.question}, fallback=True)
            fallback_check = self.checker.check('planner', fallback_output, task.model_dump())
            self._record_stage(trace, 'planner', fallback_output, fallback_check, breaker_tripped=True, used_fallback=True)
            planner_payload = self._safe_json_loads(fallback_output, {'plan': [], 'assumptions': []})
            if not fallback_check.valid:
                prior_failures += 1
        else:
            self._record_stage(trace, 'planner', planner_output, planner_check, breaker_tripped=False, used_fallback=False)
            planner_payload = self._safe_json_loads(planner_output, {'plan': [], 'assumptions': []})
            if not planner_check.valid:
                prior_failures += 1

        executor_output = self._run_stage('executor', task, payload=planner_payload, fallback=False)
        executor_check = self.checker.check('executor', executor_output, task.model_dump())
        executor_trip = self._should_trip(policy, executor_check, prior_failures, rolling_risk)
        if executor_trip:
            trace.trip_count += 1
            fallback_output = self._run_stage('executor', task, payload=planner_payload, fallback=True)
            fallback_check = self.checker.check('executor', fallback_output, task.model_dump())
            self._record_stage(trace, 'executor', fallback_output, fallback_check, breaker_tripped=True, used_fallback=True)
            executor_payload = self._safe_json_loads(
                fallback_output,
                {'candidate_answer': '', 'evidence': [], 'notes': []},
            )
            if not fallback_check.valid:
                prior_failures += 1
        else:
            self._record_stage(trace, 'executor', executor_output, executor_check, breaker_tripped=False, used_fallback=False)
            executor_payload = self._safe_json_loads(
                executor_output,
                {'candidate_answer': '', 'evidence': [], 'notes': []},
            )
            if not executor_check.valid:
                prior_failures += 1

        verifier_output = self._run_stage('verifier', task, payload=executor_payload, fallback=False)
        verifier_payload = self._safe_json_loads(verifier_output, {'final_answer': ''})
        trace.final_answer = str(verifier_payload.get('final_answer', ''))
        if not trace.final_answer.strip():
            trace.upstream_failure_seen = True
        return trace
