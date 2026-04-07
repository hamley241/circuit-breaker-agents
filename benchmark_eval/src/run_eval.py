from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

from .agent import BenchmarkAgentRunner
from .config import ModelConfig
from .gaia_loader import load_tasks
from .grader import SimpleExactMatchGrader
from .models import build_model_client
from .schemas import RunTrace


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run benchmark evaluation with circuit-breaker policies.')
    parser.add_argument('--input', required=True, help='Path to JSONL task file.')
    parser.add_argument('--policy', default='all', choices=['all', 'no_cb', 'ai_cb', 'adaptive_cb', 'completeness_cb'])
    parser.add_argument('--output', required=True, help='Path to raw JSONL output.')
    parser.add_argument('--execution-mode', default='state_locked', choices=['state_locked', 'free_recovery'])
    parser.add_argument('--pipeline-variant', default='three_stage', choices=['three_stage', 'two_stage'])
    parser.add_argument('--fault-type', default='none', choices=['none', 'structural', 'semantic'])
    parser.add_argument('--inject-rate', type=float, default=0.0)
    parser.add_argument('--mode', default='intervention', choices=['intervention', 'observer'])
    parser.add_argument('--verifier', default='', choices=['', 'handoff_only', 'handoff_plus_task', 'cross_stage'])
    parser.add_argument('--verifier-variant', default='', choices=['', 'correct', 'ablated', 'wrong_spec'])
    parser.add_argument('--compute-recoverability', action='store_true')
    parser.add_argument('--compute-oracle', action='store_true')
    return parser.parse_args()


def record_grading_details(trace: RunTrace, reference_answer: str, observed_final_answer: str, reason: str) -> None:
    trace.reference_answer = reference_answer
    trace.observed_final_answer_for_grading = observed_final_answer
    trace.grader_reason = reason
    trace.grading_reason = reason


def main() -> None:
    load_dotenv()
    args = parse_args()
    tasks = load_tasks(Path(args.input))
    model_config = ModelConfig()
    model = build_model_client(model_config)
    runner = BenchmarkAgentRunner(model=model)
    grader = SimpleExactMatchGrader()

    policies = ['no_cb', 'ai_cb', 'adaptive_cb', 'completeness_cb'] if args.policy == 'all' else [args.policy]

    history: List[RunTrace] = []
    by_policy: Dict[str, List[RunTrace]] = {p: [] for p in policies}
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open('w', encoding='utf-8') as f:
        for policy in policies:
            for task in tasks:
                previous = by_policy[policy]
                rolling_risk = (sum(1 for t in previous if t.upstream_failure_seen) / len(previous)) if previous else 0.0
                trace = runner.execute_task(
                    task=task,
                    policy=policy,
                    rolling_risk=rolling_risk,
                    execution_mode=args.execution_mode,
                    pipeline_variant=args.pipeline_variant,
                    fault_type=args.fault_type,
                    inject_rate=args.inject_rate,
                )
                trace.mode = args.mode
                trace.verifier_name = args.verifier
                trace.verifier_variant = args.verifier_variant
                trace.recoverability_computed = args.compute_recoverability
                trace.oracle_computed = args.compute_oracle
                observed_final_answer = trace.final_answer or ''
                success, reason = grader.grade(task, observed_final_answer)
                record_grading_details(trace, task.reference_answer, observed_final_answer, reason)
                trace.final_success = success
                if args.compute_oracle and not trace.final_success:
                    oracle_answer, oracle_raw_output = runner.run_stage3_oracle_from_stage1(task, trace)
                    oracle_success, _ = grader.grade(task, oracle_answer)
                    trace.oracle_stage3_from_stage1_answer = oracle_answer
                    trace.oracle_verifier_raw_output = oracle_raw_output
                    trace.oracle_stage3_from_stage1_success = oracle_success
                    trace.recoverable_handoff_failure = (
                        (trace.upstream_corrupted or trace.fault_variant != '')
                        and (not trace.final_success)
                        and trace.oracle_stage3_from_stage1_success is True
                    )
                trace.execution_mode = getattr(trace, 'execution_mode', 'state_locked')
                trace.pipeline_variant = getattr(trace, 'pipeline_variant', 'three_stage')
                trace.fault_type = getattr(trace, 'fault_type', 'none')
                trace.upstream_corrupted = getattr(trace, 'upstream_corrupted', False)
                trace.fault_variant = getattr(trace, 'fault_variant', '')
                trace.cb_tripped = getattr(trace, 'cb_tripped', False)
                trace.trip_reason = getattr(trace, 'trip_reason', '')
                trace.intermediate_valid = getattr(trace, 'intermediate_valid', True)
                trace.safe_failure = getattr(trace, 'safe_failure', False)
                trace.final_correct = success
                if trace.execution_mode == 'state_locked' and not trace.final_success:
                    trace.upstream_failure_seen = True
                trace.trip_count = getattr(trace, 'trip_count', 0)
                trace.cascade = trace.upstream_failure_seen and (not trace.final_success)
                history.append(trace)
                by_policy[policy].append(trace)
                f.write(json.dumps(trace.model_dump(), ensure_ascii=False) + '\n')

    print(f'Provider={model_config.provider} model={model_config.model_name}')
    print(f'Wrote {len(history)} traces to {output_path}')


if __name__ == '__main__':
    main()
