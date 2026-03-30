#!/usr/bin/env python3
"""
Simulator Harness for exp-001b: Circuit Breaker Reliability Study
Local simulator to iterate on breaker logic + recovery policies before Modal runs.

Mirrors the structure of experiment_runner.py but runs locally with stubbed LLM responses
for deterministic testing of circuit breaker behaviors and recovery policies.
"""
import os
import json
import time
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, is_dataclass
from collections import defaultdict

# Import circuit breaker implementations (reuse existing)
from circuit_breaker import (
    AIAdaptiveCircuitBreaker, 
    SimpleCircuitBreaker, 
    TimeoutOnlyProtection,
    NoProtection,
    CircuitConfig,
    Response,
    CircuitBreakerOpenError
)

# Workload configurations
WORKLOADS_DIR = Path(__file__).parent / "workloads"

@dataclass
class SimulatorConfig:
    """Configuration for simulator parameters."""
    workload: str = "control"  # control or stress
    runs: int = 10
    condition: str = "SIMPLE_CB"  # NO_PROTECTION, TIMEOUT_ONLY, SIMPLE_CB, AI_CB, ADAPTIVE_CB
    seed: int = 42
    turn_budget: int = 25
    verbose: bool = False
    
    def __post_init__(self):
        """Validate configuration."""
        valid_workloads = ["control", "stress"]
        if self.workload not in valid_workloads:
            raise ValueError(f"Invalid workload '{self.workload}'. Must be one of {valid_workloads}")
        
        valid_conditions = ["NO_PROTECTION", "TIMEOUT_ONLY", "SIMPLE_CB", "AI_CB", "ADAPTIVE_CB"]
        if self.condition not in valid_conditions:
            raise ValueError(f"Invalid condition '{self.condition}'. Must be one of {valid_conditions}")


@dataclass  
class FailureEvent:
    """Track failure events for CFR calculation."""
    agent_id: str
    failure_type: str
    timestamp: float
    turn_number: int
    task_id: str


@dataclass
class TimelineEvent:
    """Track timeline events for diagnostic logging."""
    timestamp: float
    turn_number: int
    event_type: str  # agent_call, circuit_trip, recovery_attempt, task_complete
    agent_id: Optional[str]
    details: Dict


class CFRTracker:
    """Tracks cascading failure rate."""
    def __init__(self, propagation_window_turns: int = 3):
        self.propagation_window = propagation_window_turns
        self.failures: List[FailureEvent] = []

    def record_failure(self, event: FailureEvent) -> None:
        """Record a failure event."""
        self.failures.append(event)

    def calculate_cfr(self) -> Dict[str, float]:
        """Calculate CFR for the experiment."""
        # Group failures by task
        task_failures: Dict[str, List[FailureEvent]] = defaultdict(list)
        for f in self.failures:
            task_failures[f.task_id].append(f)

        initial_count = 0
        cascaded_count = 0

        for task_id, task_fails in task_failures.items():
            if not task_fails:
                continue

            # Sort by turn number
            sorted_fails = sorted(task_fails, key=lambda x: x.turn_number)
            initial_count += 1
            initial_failure = sorted_fails[0]

            # Check for cascades within window
            for subsequent in sorted_fails[1:]:
                turn_delta = subsequent.turn_number - initial_failure.turn_number
                if turn_delta <= self.propagation_window:
                    cascaded_count += 1
                    break  # Only count one cascade per task

        contained_count = initial_count - cascaded_count
        cfr = cascaded_count / initial_count if initial_count > 0 else 0.0

        return {
            "cfr_rate": cfr,
            "initial_failures": initial_count,
            "cascaded_failures": cascaded_count,
            "contained_failures": contained_count,
            "total_tasks_with_failure": len(task_failures),
        }


class WorkloadLoader:
    """Load and manage workload configurations."""
    
    @staticmethod
    def load_workload(workload_name: str) -> Dict:
        """Load workload configuration from workloads directory."""
        workload_dir = WORKLOADS_DIR / workload_name
        if not workload_dir.exists():
            raise FileNotFoundError(f"Workload directory not found: {workload_dir}")
        
        config_file = workload_dir / "config.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Workload config not found: {config_file}")
        
        with open(config_file) as f:
            return json.load(f)


class StubLLMSystem:
    """Stubbed LLM system for deterministic testing."""
    
    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.workload_config = WorkloadLoader.load_workload(config.workload)
        self.rng = random.Random(config.seed)
        
    def should_inject_failure(self, failure_type: str, run_id: str, turn_number: int) -> bool:
        """Determine if we should inject a failure (deterministic based on seed)."""
        # Use seeded random for reproducibility
        failure_seed = hash(f"{self.config.seed}_{run_id}_{turn_number}_{failure_type}")
        failure_rng = random.Random(failure_seed)
        
        # Get failure rates from workload config
        failure_rates = self.workload_config.get("failure_rates", {
            "api_timeout": 0.1,
            "confidence_decay": 0.15,
            "context_overflow": 0.08,
            "cascading_hallucination": 0.12,
        })
        
        rate = failure_rates.get(failure_type, 0.05)
        return failure_rng.random() < rate
    
    def generate_response(self, agent_id: str, run_id: str, turn_number: int, 
                         context: Optional[str] = None) -> Response:
        """Generate a stubbed response for the given agent."""
        # Get agent-specific prompts from workload
        agent_prompts = self.workload_config.get("agent_prompts", {})
        prompt = agent_prompts.get(agent_id, f"Default prompt for {agent_id}")
        
        # Deterministic seed for this specific call
        response_seed = hash(f"{self.config.seed}_{run_id}_{agent_id}_{turn_number}")
        response_rng = random.Random(response_seed)
        
        # Check for failure injection
        if self.should_inject_failure("api_timeout", run_id, turn_number):
            raise TimeoutError("Simulated API timeout")
        
        if self.should_inject_failure("confidence_decay", run_id, turn_number):
            return Response(
                content=f"Low confidence response from {agent_id}",
                confidence=0.2,
                token_usage=response_rng.randint(800, 1200),
                reasoning="Uncertain about this response"
            )
        
        if self.should_inject_failure("context_overflow", run_id, turn_number):
            return Response(
                content=f"Partial response due to context limits from {agent_id}",
                confidence=0.7,
                token_usage=8500,  # Over threshold
                reasoning="Ran out of context window"
            )
        
        # Normal successful response
        expected_outputs = self.workload_config.get("expected_outputs", {})
        default_output = expected_outputs.get(agent_id, f"Successful response from {agent_id}")
        
        return Response(
            content=default_output,
            confidence=response_rng.uniform(0.7, 0.95),
            token_usage=response_rng.randint(500, 2000),
            reasoning=f"Processed request successfully in {agent_id}"
        )


class SimulatedMultiAgentSystem:
    """
    Simulated multi-agent system mirroring the real experiment_runner structure.
    Supports both control and stress workloads with stubbed responses.
    """
    def __init__(self, config: SimulatorConfig, run_id: str):
        self.config = config
        self.run_id = run_id
        self.turn_number = 0
        self.task_id = f"{run_id}"
        self.cfr_tracker = CFRTracker()
        self.timeline: List[TimelineEvent] = []
        self.stub_llm = StubLLMSystem(config)
        
        # Circuit breaker based on condition
        self.cb_agent_a = self._create_circuit_breaker()
        self.cb_agent_b = self._create_circuit_breaker()
        
        # Metrics
        self.metrics = {
            "agent_a_failures": 0,
            "agent_b_failures": 0,
            "circuit_trips": 0,
            "recovery_attempts": 0,
            "task_completed": False,
            "total_turns": 0,
            "total_token_usage": 0,
        }
        
        # Recovery policies
        self.recovery_policies = {
            "TIMEOUT_ONLY": self._retry_policy,
            "SIMPLE_CB": self._skip_and_continue_policy,
            "AI_CB": self._alternate_model_policy,
            "ADAPTIVE_CB": self._safe_mode_policy,
        }

    def _create_circuit_breaker(self):
        """Create circuit breaker based on condition."""
        if self.config.condition == "NO_PROTECTION":
            return NoProtection()
        elif self.config.condition == "TIMEOUT_ONLY":
            return TimeoutOnlyProtection(timeout_seconds=30.0)
        elif self.config.condition == "SIMPLE_CB":
            return SimpleCircuitBreaker(failure_threshold=1, timeout_seconds=15.0)
        elif self.config.condition == "AI_CB":
            config = CircuitConfig(
                confidence_threshold=0.6,
                context_threshold=6000,
                predictability_min=0.3,
                failure_threshold=1,
                timeout_seconds=20.0
            )
            return AIAdaptiveCircuitBreaker(config)
        elif self.config.condition == "ADAPTIVE_CB":
            config = CircuitConfig(
                confidence_threshold=0.7,
                context_threshold=5000,
                predictability_min=0.4,
                failure_threshold=1,
                timeout_seconds=15.0
            )
            return AIAdaptiveCircuitBreaker(config)
        else:
            return NoProtection()

    def _log_timeline_event(self, event_type: str, agent_id: Optional[str] = None, **details):
        """Log a timeline event."""
        event = TimelineEvent(
            timestamp=time.time(),
            turn_number=self.turn_number,
            event_type=event_type,
            agent_id=agent_id,
            details=details
        )
        self.timeline.append(event)
        
        if self.config.verbose:
            print(f"  Turn {self.turn_number}: {event_type} ({agent_id}) - {details}")

    def _retry_policy(self, agent_id: str, original_error: Exception) -> Optional[Response]:
        """Recovery policy: retry once, then fail subtask."""
        self.metrics["recovery_attempts"] += 1
        self._log_timeline_event("recovery_attempt", agent_id, policy="retry", error=str(original_error))
        
        try:
            # Attempt one retry
            return self.stub_llm.generate_response(agent_id, f"{self.run_id}_retry", self.turn_number)
        except Exception as retry_error:
            self._log_timeline_event("recovery_failed", agent_id, retry_error=str(retry_error))
            return None

    def _skip_and_continue_policy(self, agent_id: str, original_error: Exception) -> Optional[Response]:
        """Recovery policy: skip failing agent, continue with remaining plan."""
        self.metrics["recovery_attempts"] += 1
        self._log_timeline_event("recovery_attempt", agent_id, policy="skip_continue", error=str(original_error))
        
        return Response(
            content=f"Skipped {agent_id} due to circuit breaker protection",
            confidence=0.5,
            token_usage=0,
            reasoning=f"Circuit breaker prevented call to {agent_id}"
        )

    def _alternate_model_policy(self, agent_id: str, original_error: Exception) -> Optional[Response]:
        """Recovery policy: alternate prompt/model (simulate Claude ↔ GPT-4o)."""
        self.metrics["recovery_attempts"] += 1
        self._log_timeline_event("recovery_attempt", agent_id, policy="alternate_model", error=str(original_error))
        
        # Simulate switching to alternate model with different characteristics
        alternate_seed = hash(f"{self.config.seed}_{self.run_id}_alt_{agent_id}_{self.turn_number}")
        alt_rng = random.Random(alternate_seed)
        
        return Response(
            content=f"Alternate model response from {agent_id}",
            confidence=alt_rng.uniform(0.6, 0.85),
            token_usage=alt_rng.randint(800, 1800),
            reasoning=f"Recovered using alternate model for {agent_id}"
        )

    def _safe_mode_policy(self, agent_id: str, original_error: Exception) -> Optional[Response]:
        """Recovery policy: route to safe-mode workflow with degraded objectives."""
        self.metrics["recovery_attempts"] += 1
        self._log_timeline_event("recovery_attempt", agent_id, policy="safe_mode", error=str(original_error))
        
        return Response(
            content=f"Safe-mode response from {agent_id} with reduced functionality",
            confidence=0.6,
            token_usage=500,  # Lower token usage
            reasoning=f"Safe-mode workflow activated for {agent_id} due to circuit protection"
        )

    def _simulate_agent(self, agent_id: str) -> Tuple[Optional[Response], bool]:
        """Simulate agent execution with circuit breaker protection and recovery."""
        self.turn_number += 1
        self._log_timeline_event("agent_call", agent_id, turn=self.turn_number)
        
        circuit_breaker = self.cb_agent_a if agent_id == "agent_a" else self.cb_agent_b
        
        try:
            # Attempt the agent call through circuit breaker
            def agent_work():
                return self.stub_llm.generate_response(agent_id, self.run_id, self.turn_number)
            
            result = circuit_breaker.call(agent_work)
            self.metrics["total_token_usage"] += result.token_usage
            self._log_timeline_event("agent_success", agent_id, 
                                   confidence=result.confidence, tokens=result.token_usage)
            return result, True
            
        except CircuitBreakerOpenError as cb_error:
            self.metrics["circuit_trips"] += 1
            self._log_timeline_event("circuit_trip", agent_id, error=str(cb_error))
            
            # Attempt recovery using the appropriate policy
            recovery_policy = self.recovery_policies.get(self.config.condition)
            if recovery_policy:
                recovery_result = recovery_policy(agent_id, cb_error)
                if recovery_result:
                    self.metrics["total_token_usage"] += recovery_result.token_usage
                    self._log_timeline_event("recovery_success", agent_id, 
                                           policy=self.config.condition)
                    return recovery_result, True
            
            # Recovery failed or no recovery policy
            self._log_timeline_event("recovery_failed", agent_id)
            return None, False
            
        except Exception as e:
            # Handle other failures (timeouts, etc.)
            if agent_id == "agent_a":
                self.metrics["agent_a_failures"] += 1
            else:
                self.metrics["agent_b_failures"] += 1
                
            self.cfr_tracker.record_failure(FailureEvent(
                agent_id=agent_id, 
                failure_type=type(e).__name__,
                timestamp=time.time(), 
                turn_number=self.turn_number, 
                task_id=self.task_id
            ))
            
            self._log_timeline_event("agent_failure", agent_id, 
                                   error=str(e), error_type=type(e).__name__)
            
            # Attempt recovery
            recovery_policy = self.recovery_policies.get(self.config.condition)
            if recovery_policy:
                recovery_result = recovery_policy(agent_id, e)
                if recovery_result:
                    self.metrics["total_token_usage"] += recovery_result.token_usage
                    return recovery_result, True
            
            return None, False

    def _response_to_dict(self, response: Response) -> Dict:
        """Convert Response object to dictionary."""
        return {
            "content": response.content,
            "confidence": response.confidence,
            "token_usage": response.token_usage,
            "reasoning": response.reasoning
        }

    def run_task(self) -> Dict:
        """Run a single collaborative task."""
        self._log_timeline_event("task_start", details={"workload": self.config.workload})
        
        # Agent A execution
        agent_a_result, agent_a_success = self._simulate_agent("agent_a")
        
        # Agent B execution (may cascade from Agent A failure)
        agent_b_result, agent_b_success = self._simulate_agent("agent_b")
        
        # Check for cascading failures
        if not agent_a_success and not agent_b_success:
            # Potential cascade - check if circuit breaker prevented it
            if self.metrics["circuit_trips"] > 0 and self.metrics["recovery_attempts"] > 0:
                self._log_timeline_event("cascade_prevented", 
                                       details={"circuit_trips": self.metrics["circuit_trips"]})
            else:
                self._log_timeline_event("cascade_occurred")
        
        self.metrics["task_completed"] = agent_a_success and agent_b_success
        self.metrics["total_turns"] = self.turn_number
        
        self._log_timeline_event("task_complete", 
                               details={"success": self.metrics["task_completed"]})
        
        # Get circuit breaker metrics
        cb_metrics_a = getattr(self.cb_agent_a, 'get_metrics', lambda: {})()
        cb_metrics_b = getattr(self.cb_agent_b, 'get_metrics', lambda: {})()
        
        return {
            "run_id": self.run_id,
            "condition": self.config.condition,
            "workload": self.config.workload,
            "task_completed": self.metrics["task_completed"],
            "metrics": self.metrics,
            "cfr": self.cfr_tracker.calculate_cfr(),
            "circuit_breaker_a": cb_metrics_a,
            "circuit_breaker_b": cb_metrics_b,
            "timeline": [asdict(event) for event in self.timeline],
            "agent_a_result": self._response_to_dict(agent_a_result) if agent_a_result else None,
            "agent_b_result": self._response_to_dict(agent_b_result) if agent_b_result else None,
        }


class SimulatorRunner:
    """Orchestrates the full simulator experiment."""
    
    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.results: List[Dict] = []
        
        # Set up deterministic randomness
        random.seed(config.seed)
        
    def run_all(self) -> Dict:
        """Run the full simulation."""
        print(f"\n{'='*60}")
        print(f"exp-001b Simulator - {self.config.condition}")
        print(f"Workload: {self.config.workload} | Runs: {self.config.runs} | Seed: {self.config.seed}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        for i in range(self.config.runs):
            run_id = f"{self.config.condition}_{self.config.workload}_{i:03d}"
            
            if self.config.verbose:
                print(f"\nRun {i+1}/{self.config.runs}: {run_id}")
            
            system = SimulatedMultiAgentSystem(self.config, run_id)
            result = system.run_task()
            self.results.append(result)
            
            # Progress indicator
            if not self.config.verbose and (i + 1) % 5 == 0:
                print(f"  Completed {i + 1}/{self.config.runs}")
        
        elapsed = time.time() - start_time
        summary = self._calculate_summary()
        summary["elapsed_seconds"] = elapsed
        summary["config"] = asdict(self.config)
        
        self._print_summary(summary)
        return summary
    
    def _calculate_summary(self) -> Dict:
        """Calculate experiment summary statistics."""
        if not self.results:
            return {"runs": 0}
        
        total_cfr = sum(r["cfr"]["cfr_rate"] for r in self.results)
        avg_cfr = total_cfr / len(self.results)
        completed = sum(1 for r in self.results if r["task_completed"])
        
        total_token_usage = sum(r["metrics"]["total_token_usage"] for r in self.results)
        total_recovery_attempts = sum(r["metrics"]["recovery_attempts"] for r in self.results)
        total_circuit_trips = sum(r["metrics"]["circuit_trips"] for r in self.results)
        
        return {
            "runs": len(self.results),
            "avg_cfr": round(avg_cfr, 4),
            "completion_rate": round(completed / len(self.results), 4),
            "total_token_usage": total_token_usage,
            "avg_token_usage_per_run": round(total_token_usage / len(self.results), 2),
            "total_recovery_attempts": total_recovery_attempts,
            "total_circuit_trips": total_circuit_trips,
            "protection_activation_rate": round(total_circuit_trips / len(self.results), 4),
        }
    
    def _print_summary(self, summary: Dict) -> None:
        """Print formatted summary."""
        print(f"\n{'='*60}")
        print("SIMULATOR RESULTS SUMMARY")
        print(f"{'='*60}")
        print(f"Runs completed: {summary['runs']}")
        print(f"Completion rate: {summary['completion_rate']:.4f}")
        print(f"Average CFR: {summary['avg_cfr']:.4f}")
        print(f"Total token usage: {summary['total_token_usage']:,}")
        print(f"Avg tokens/run: {summary['avg_token_usage_per_run']:.0f}")
        print(f"Circuit trips: {summary['total_circuit_trips']}")
        print(f"Recovery attempts: {summary['total_recovery_attempts']}")
        print(f"Protection activation: {summary['protection_activation_rate']:.4f}")
        print(f"Elapsed time: {summary.get('elapsed_seconds', 0):.2f}s")


def main():
    parser = argparse.ArgumentParser(
        description="Local simulator for exp-001b circuit breaker experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python simulator.py --workload control --runs 10 --condition SIMPLE_CB --seed 42
  python simulator.py --workload stress --runs 5 --condition AI_CB --verbose
  python simulator.py --workload control --runs 20 --condition ADAPTIVE_CB --output results.json
        """
    )
    
    parser.add_argument("--workload", default="control", 
                       help="Workload type: control or stress (default: control)")
    parser.add_argument("--runs", type=int, default=10,
                       help="Number of runs to execute (default: 10)")
    parser.add_argument("--condition", default="SIMPLE_CB",
                       help="Protection condition: NO_PROTECTION, TIMEOUT_ONLY, SIMPLE_CB, AI_CB, ADAPTIVE_CB (default: SIMPLE_CB)")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--turn-budget", type=int, default=25,
                       help="Turn budget per run (default: 25)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output with per-turn logging")
    parser.add_argument("--output", "-o", type=str,
                       help="Output JSON file for results")
    
    args = parser.parse_args()
    
    try:
        config = SimulatorConfig(
            workload=args.workload,
            runs=args.runs,
            condition=args.condition,
            seed=args.seed,
            turn_budget=args.turn_budget,
            verbose=args.verbose
        )
        
        runner = SimulatorRunner(config)
        results = runner.run_all()
        
        # Add runs data to results
        results["runs"] = runner.results
        
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(json.dumps(results, indent=2))
            print(f"\nResults saved to: {output_path}")
        
        return results
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    main()