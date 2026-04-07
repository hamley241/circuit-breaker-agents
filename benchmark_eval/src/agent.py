from __future__ import annotations

import json
import random
import re
from typing import Any, Dict, List

from .breaker import AdaptiveBreaker, StaticBreaker
from .checker import Checker
from .config import BreakerConfig, PROMPTS_DIR
from .models import BaseModelClient
from .schemas import CheckerResult, IntermediateHandoff, RunTrace, StageTrace, TaskRecord
from .utils import load_text


class BenchmarkAgentRunner:
    _BARE_VALUE_INSTRUCTION = (
        "\"final_answer\" must contain only the answer value itself — a number, word, or JSON value. "
        "Do not include any explanation, reasoning, units, symbols, or working. Return only the bare value."
    )

    def __init__(self, model: BaseModelClient, breaker_config: BreakerConfig | None = None):
        self.model = model
        self.checker = Checker(model)
        self.static_breaker = StaticBreaker(breaker_config or BreakerConfig())
        self.adaptive_breaker = AdaptiveBreaker(breaker_config or BreakerConfig())

    def _prompt_for(self, stage: str, fallback: bool) -> str:
        filename = f"fallback_{stage}.txt" if fallback else f"{stage}.txt"
        return load_text(PROMPTS_DIR / filename)

    def _verifier_prompt(self, execution_mode: str, fallback: bool) -> str:
        prompt = self._prompt_for('verifier', fallback=fallback)
        if execution_mode != 'state_locked':
            return prompt
        prompt = prompt.replace(self._BARE_VALUE_INSTRUCTION, '').rstrip()
        return (
            prompt
            + "\n"
            + "In state_locked mode, use only intermediate_handoff as the authoritative intermediate state.\n"
            + "Do not use or infer missing values from the original question.\n"
            + "Do not infer or recover planner or executor state beyond what is present in intermediate_handoff.\n"
            + "Do not correct wrong values.\n"
            + "Preserve the provided state even if it appears inconsistent.\n"
            + self._BARE_VALUE_INSTRUCTION
            + "\n"
        )

    def _run_stage(self, stage: str, task: TaskRecord, payload: Dict[str, Any], fallback: bool) -> str:
        prompt = self._prompt_for(stage, fallback=fallback)
        response = self.model.generate(
            prompt=prompt,
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
            # Symptom-based flag: observed stage degradation during execution.
            trace.upstream_failure_seen = True

    def _should_trip(self, policy: str, checker: CheckerResult, prior_failures: int, rolling_risk: float) -> bool:
        if policy == 'no_cb':
            return False
        if policy == 'completeness_cb':
            return False
        if policy == 'ai_cb':
            return self.static_breaker.should_trip(checker)
        if policy == 'adaptive_cb':
            return self.adaptive_breaker.should_trip(checker, prior_failures=prior_failures, rolling_risk=rolling_risk)
        raise ValueError(f'Unknown policy: {policy}')

    @staticmethod
    def _handoff_has_numeric_values(handoff: IntermediateHandoff | None) -> bool:
        if handoff is None:
            return False
        haystacks = [handoff.summary, *handoff.facts]
        for text in haystacks:
            if re.search(r'(?<![A-Za-z])[+-]?\d+(?:\.\d+)?(?![A-Za-z])', text):
                return True
        return False

    @staticmethod
    def _safe_json_loads(raw_text: str, default: Dict[str, Any]) -> Dict[str, Any]:
        try:
            parsed = json.loads(raw_text)
            return parsed if isinstance(parsed, dict) else default
        except Exception:
            return default

    @staticmethod
    def _as_str_list(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    def _build_intermediate_handoff(self, planner_payload: Dict[str, Any]) -> IntermediateHandoff | None:
        plan_steps = self._as_str_list(planner_payload.get('plan'))
        assumptions = self._as_str_list(planner_payload.get('assumptions'))
        givens = planner_payload.get('givens') or {}
        givens_facts = [f"{k}={v}" for k, v in givens.items()] if isinstance(givens, dict) else []
        facts = givens_facts + plan_steps + assumptions
        summary = ' '.join(plan_steps).strip()
        if not summary and facts:
            summary = facts[0]
        if not summary and not facts:
            return None
        return IntermediateHandoff(
            summary=summary,
            facts=facts,
            confidence=1.0,
        )

    @staticmethod
    def _handoff_to_dict(handoff: IntermediateHandoff | None) -> Dict[str, Any]:
        if handoff is None:
            return {'summary': '', 'facts': [], 'confidence': 0.0}
        return {
            'summary': handoff.summary,
            'facts': handoff.facts,
            'confidence': handoff.confidence,
        }

    def _planner_payload_to_handoff_dict(self, planner_payload: Dict[str, Any]) -> Dict[str, Any]:
        plan_steps = self._as_str_list(planner_payload.get('plan'))
        assumptions = self._as_str_list(planner_payload.get('assumptions'))
        givens = planner_payload.get('givens') or {}
        givens_facts = [f"{k}={v}" for k, v in givens.items()] if isinstance(givens, dict) else []
        facts = givens_facts + plan_steps + assumptions
        summary = ' '.join(plan_steps).strip()
        if not summary and facts:
            summary = facts[0]
        return {
            'summary': summary,
            'facts': facts,
            'confidence': 1.0 if summary or facts else 0.0,
        }

    @staticmethod
    def _match_case(replacement: str, original: str) -> str:
        if original.isupper():
            return replacement.upper()
        if original[:1].isupper():
            return replacement.capitalize()
        return replacement

    @staticmethod
    def _flip_operation_words(text: str) -> str:
        replacements = {
            'increase': 'decrease',
            'decrease': 'increase',
            'add': 'subtract',
            'subtract': 'add',
            'before': 'after',
            'after': 'before',
        }
        lower_text = text.lower()
        for source, target in replacements.items():
            start = lower_text.find(source)
            if start == -1:
                continue
            end = start + len(source)
            before_ok = start == 0 or not lower_text[start - 1].isalnum()
            after_ok = end == len(lower_text) or not lower_text[end].isalnum()
            if not (before_ok and after_ok):
                continue
            original = text[start:end]
            replacement = BenchmarkAgentRunner._match_case(target, original)
            return text[:start] + replacement + text[end:]
        return text

    def _inject_intermediate_fault(self, handoff: IntermediateHandoff, fault_type: str) -> tuple[IntermediateHandoff, str]:
        if fault_type == 'structural':
            variants = ['empty_handoff', 'partial_handoff', 'reordered_degraded_handoff']
            variant = random.choice(variants)
            if variant == 'empty_handoff':
                return IntermediateHandoff(summary='', facts=[], confidence=0.0), variant
            if variant == 'partial_handoff':
                return (
                    IntermediateHandoff(
                        summary=handoff.summary,
                        facts=handoff.facts[:1],
                        confidence=max(0.0, handoff.confidence - 0.35),
                    ),
                    variant,
                )
            degraded_facts = list(handoff.facts)
            if degraded_facts:
                degraded_facts = degraded_facts[1:] + degraded_facts[:1]
                if len(degraded_facts) == 1:
                    degraded_facts.append(degraded_facts[0])
            return (
                IntermediateHandoff(
                    summary=handoff.summary[: max(1, len(handoff.summary) // 2)].strip(),
                    facts=degraded_facts,
                    confidence=max(0.0, handoff.confidence - 0.45),
                ),
                variant,
            )
        if fault_type == 'semantic':
            variants = ['summary_drift', 'fact_drift', 'step_reorder']
            variant = random.choice(variants)
            if variant == 'summary_drift':
                return (
                    IntermediateHandoff(
                        summary=self._flip_operation_words(handoff.summary),
                        facts=handoff.facts,
                        confidence=max(0.0, handoff.confidence - 0.25),
                    ),
                    variant,
                )
            if variant == 'fact_drift':
                drifted_facts = list(handoff.facts)
                if drifted_facts:
                    drifted_facts[0] = self._flip_operation_words(drifted_facts[0])
                return (
                    IntermediateHandoff(
                        summary=handoff.summary,
                        facts=drifted_facts,
                        confidence=max(0.0, handoff.confidence - 0.25),
                    ),
                    variant,
                )
            return (
                IntermediateHandoff(
                    summary=handoff.summary,
                    facts=list(reversed(handoff.facts)),
                    confidence=max(0.0, handoff.confidence - 0.3),
                ),
                variant,
            )
        return handoff, ''

    @staticmethod
    def _normalize_executor_answer(candidate_answer: str) -> str:
        cleaned = (candidate_answer or '').strip()
        if not cleaned:
            return ''
        cleaned = re.sub(r'[*_`]', '', cleaned).strip()
        cleaned = re.sub(r'^(final answer|answer)\s*:\s*', '', cleaned, flags=re.IGNORECASE).strip()

        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if lines:
            cleaned = lines[-1]

        trailing_literal = re.search(r'([+-]?\d+(?:\.\d+)?|[A-Za-z]{1,12})\s*$', cleaned)
        if trailing_literal:
            prefix = cleaned[: trailing_literal.start()].rstrip(' :;,-')
            if not prefix or prefix.lower().endswith(('is', 'was', 'are', 'equals', 'answer')):
                return trailing_literal.group(1)
        return cleaned

    def execute_task(
        self,
        task: TaskRecord,
        policy: str,
        rolling_risk: float = 0.0,
        execution_mode: str = 'state_locked',
        pipeline_variant: str = 'three_stage',
        fault_type: str = 'none',
        inject_rate: float = 0.0,
    ) -> RunTrace:
        trace = RunTrace(task_id=task.task_id, policy=policy, execution_mode=execution_mode, pipeline_variant=pipeline_variant, fault_type=fault_type)
        prior_failures = 0

        planner_output = self._run_stage('planner', task, payload={'question': task.question}, fallback=False)
        planner_check = self.checker.check('planner', planner_output, task.model_dump())
        planner_trip = self._should_trip(policy, planner_check, prior_failures, rolling_risk)
        if planner_trip:
            trace.trip_count += 1
            fallback_output = self._run_stage('planner', task, payload={'question': task.question}, fallback=True)
            fallback_check = self.checker.check('planner', fallback_output, task.model_dump())
            self._record_stage(trace, 'planner', fallback_output, fallback_check, breaker_tripped=True, used_fallback=True)
            planner_payload = self._safe_json_loads(fallback_output, {'givens': {}, 'plan': [], 'assumptions': []})
            if not fallback_check.valid:
                prior_failures += 1
        else:
            self._record_stage(trace, 'planner', planner_output, planner_check, breaker_tripped=False, used_fallback=False)
            planner_payload = self._safe_json_loads(planner_output, {'givens': {}, 'plan': [], 'assumptions': []})
            if not planner_check.valid:
                prior_failures += 1
        trace.stage1_output = planner_payload

        intermediate_handoff = self._build_intermediate_handoff(planner_payload)
        if intermediate_handoff is not None and inject_rate > 0.0 and random.random() < inject_rate:
            intermediate_handoff, trace.fault_variant = self._inject_intermediate_fault(intermediate_handoff, fault_type=fault_type)
            # Cause-based flag: this run received an injected upstream corruption.
            trace.upstream_corrupted = True
        if intermediate_handoff is None:
            # Symptom-based flag: handoff construction failed.
            trace.upstream_failure_seen = True
        trace.intermediate_valid = bool(intermediate_handoff is not None and intermediate_handoff.summary.strip() and intermediate_handoff.facts)
        trace.handoff_has_numeric_values = self._handoff_has_numeric_values(intermediate_handoff)
        if trace.upstream_corrupted and not trace.intermediate_valid:
            trace.upstream_failure_seen = True
        trace.stage2_handoff = self._handoff_to_dict(intermediate_handoff)
        trace.stages.append(
            StageTrace(
                stage='intermediate_handoff',
                raw_output=trace.stage2_handoff,
                checker=CheckerResult(valid=trace.intermediate_valid, confidence=1.0 if trace.intermediate_valid else 0.0),
                breaker_tripped=False,
                used_fallback=False,
            )
        )

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

        if pipeline_variant == 'two_stage':
            trace.final_answer = self._normalize_executor_answer(str(executor_payload.get('candidate_answer', '')))
            if not trace.final_answer.strip():
                trace.upstream_failure_seen = True
            return trace

        if execution_mode == 'state_locked':
            verifier_payload_input = {
                'intermediate_handoff': self._handoff_to_dict(intermediate_handoff),
            }
            trace.verifier_input_source = 'intermediate_handoff_only'
        else:
            verifier_payload_input = executor_payload
            trace.verifier_input_source = 'default'

        completeness_trip = (
            policy == 'completeness_cb'
            and execution_mode == 'state_locked'
            and not trace.handoff_has_numeric_values
        )
        if completeness_trip:
            trace.trip_count += 1
            trace.cb_tripped = True
            trace.trip_reason = 'missing_numeric_values'
            fallback_output = self._run_stage('verifier', task, payload=verifier_payload_input, fallback=True)
            verifier_payload = self._safe_json_loads(fallback_output, {'final_answer': ''})
            trace.stages.append(
                StageTrace(
                    stage='verifier',
                    raw_output=fallback_output,
                    checker=CheckerResult(valid=bool(str(verifier_payload.get('final_answer', '')).strip()), confidence=1.0),
                    breaker_tripped=True,
                    used_fallback=True,
                )
            )
            trace.final_answer = str(verifier_payload.get('final_answer', ''))
            if not trace.final_answer.strip():
                trace.upstream_failure_seen = True
            return trace
        if execution_mode == 'state_locked':
            verifier_output = self.model.generate(
                prompt=self._verifier_prompt(execution_mode=execution_mode, fallback=False),
                context={
                    'stage': 'verifier',
                    'task': {'task_id': task.task_id},
                    'payload': verifier_payload_input,
                    'fallback': False,
                },
            ).text
        else:
            verifier_output = self._run_stage('verifier', task, payload=verifier_payload_input, fallback=False)
        verifier_payload = self._safe_json_loads(verifier_output, {'final_answer': ''})
        trace.stages.append(
            StageTrace(
                stage='verifier',
                raw_output=verifier_output,
                checker=CheckerResult(valid=bool(str(verifier_payload.get('final_answer', '')).strip()), confidence=1.0),
                breaker_tripped=False,
                used_fallback=False,
            )
        )
        trace.final_answer = str(verifier_payload.get('final_answer', ''))
        if not trace.final_answer.strip():
            # Symptom-based flag: downstream produced no usable final answer.
            trace.upstream_failure_seen = True
        return trace

    def run_stage3_oracle_from_stage1(self, task: TaskRecord, trace: RunTrace) -> tuple[str, str]:
        # Oracle-only adapter: reshape raw planner_payload into the minimal
        # handoff schema so oracle failure reflects information insufficiency,
        # not a prompt/schema mismatch.
        oracle_handoff = self._planner_payload_to_handoff_dict(trace.stage1_output or {})
        verifier_output = self.model.generate(
            prompt=self._verifier_prompt(execution_mode='state_locked', fallback=False),
            context={
                'stage': 'verifier',
                'task': {'task_id': task.task_id},
                'payload': {'intermediate_handoff': oracle_handoff},
                'fallback': False,
            },
        ).text
        verifier_payload = self._safe_json_loads(verifier_output, {'final_answer': ''})
        return str(verifier_payload.get('final_answer', '')), verifier_output
