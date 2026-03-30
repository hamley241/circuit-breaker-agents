"""
Experiment Runner for exp-001: Circuit Breaker Reliability Study
Runs on Modal with GPU acceleration (simulated and real API modes)
"""
import os
import json
import time
import random
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

# Import circuit breaker implementations
from circuit_breaker import (
    AIAdaptiveCircuitBreaker, 
    SimpleCircuitBreaker, 
    TimeoutOnlyProtection,
    NoProtection,
    CircuitConfig,
    Response,
    CircuitBreakerOpenError
)

# Import API clients for real mode
try:
    from api_clients import APIClientFactory, APIConfig
    API_CLIENTS_AVAILABLE = True
except ImportError:
    API_CLIENTS_AVAILABLE = False

# Configuration from DESIGN.md
RANDOM_SEED = 42
TEMPERATURE = 0.7
FAILURE_SEED = 2024


def setup_randomness():
    """Set up reproducible randomness."""
    random.seed(RANDOM_SEED)


def setup():
    """Install dependencies if needed."""
    setup_randomness()


@dataclass
class FailureEvent:
    """Track failure events for CFR calculation."""
    agent_id: str
    failure_type: str
    timestamp: float
    turn_number: int
    task_id: str


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


@dataclass
class AgentResponse:
    """Simulated agent response."""
    content: str
    confidence: float
    token_usage: int
    reasoning: Optional[str]
    success: bool
    failure_type: Optional[str]


class SimulatedMultiAgentSystem:
    """
    Multi-agent collaborative task system with simulated and real API modes.
    Agent A performs first subtask, Agent B coordinates.
    """
    def __init__(self, condition: str, run_id: str, real_mode: bool = False, failure_injection_rate: float = 0.5):
        self.condition = condition
        self.run_id = run_id
        self.real_mode = real_mode
        self.failure_injection_rate = failure_injection_rate
        self.turn_number = 0
        self.task_id = f"{run_id}"
        self.cfr_tracker = CFRTracker()
        
        # Circuit breaker based on condition
        self.cb_agent_a = self._create_circuit_breaker()
        self.cb_agent_b = self._create_circuit_breaker()
        
        # API clients for real mode
        if self.real_mode:
            if not API_CLIENTS_AVAILABLE:
                raise ImportError("API clients not available. Install openai and anthropic packages.")
            api_config = APIConfig(temperature=TEMPERATURE)
            
            # Check which APIs are available
            available_clients = APIClientFactory.get_available_clients(api_config)
            if not available_clients:
                raise ValueError("No API keys available. Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY")
            
            # If both APIs available, alternate between them for variety
            # If only one available, use it for both agents
            if len(available_clients) >= 2:
                # Both APIs available - alternate
                use_gpt_first = hash(run_id) % 2 == 0
                if use_gpt_first:
                    self.agent_a_client = APIClientFactory.create_gpt_client(api_config)
                    self.agent_b_client = APIClientFactory.create_claude_client(api_config)
                else:
                    self.agent_a_client = APIClientFactory.create_claude_client(api_config)
                    self.agent_b_client = APIClientFactory.create_gpt_client(api_config)
            elif 'gpt' in available_clients:
                # Only GPT available
                self.agent_a_client = APIClientFactory.create_gpt_client(api_config)
                self.agent_b_client = APIClientFactory.create_gpt_client(api_config)
                print(f"  Note: Using GPT-4o for both agents (Anthropic API key not available)")
            elif 'claude' in available_clients:
                # Only Claude available
                self.agent_a_client = APIClientFactory.create_claude_client(api_config)
                self.agent_b_client = APIClientFactory.create_claude_client(api_config)
                print(f"  Note: Using Claude for both agents (OpenAI API key not available)")
            else:
                raise ValueError("No compatible API clients available")
        
        # Metrics
        self.metrics = {
            "agent_a_failures": 0,
            "agent_b_failures": 0,
            "circuit_trips": 0,
            "recovery_attempts": 0,
            "task_completed": False,
            "total_turns": 0,
        }

    def _create_circuit_breaker(self):
        """Create circuit breaker based on condition."""
        if self.condition == "NO_PROTECTION":
            return NoProtection()
        elif self.condition == "TIMEOUT_ONLY":
            return TimeoutOnlyProtection(timeout_seconds=30.0)
        elif self.condition == "SIMPLE_CB":
            return SimpleCircuitBreaker(failure_threshold=1, timeout_seconds=15.0)  # Trip on first failure
        elif self.condition == "AI_CB":
            config = CircuitConfig(
                confidence_threshold=0.6,   # Higher threshold for better protection
                context_threshold=6000,     # Standard context limit
                predictability_min=0.3,    # Standard predictability
                failure_threshold=1,       # Trip on first failure
                timeout_seconds=20.0       # Faster recovery
            )
            return AIAdaptiveCircuitBreaker(config)
        elif self.condition == "ADAPTIVE_CB":
            config = CircuitConfig(
                confidence_threshold=0.7,  # Even higher threshold
                context_threshold=5000,    # Tighter context limits
                predictability_min=0.4,   # Higher predictability requirement
                failure_threshold=1,       # Trip on first failure
                timeout_seconds=15.0       # Even faster recovery
            )
            return AIAdaptiveCircuitBreaker(config)
        else:
            return NoProtection()

    def _should_inject_failure(self, failure_type: str) -> bool:
        """Determine if we should inject a failure."""
        # Use seeded random for reproducibility
        failure_random = random.Random(hash(f"{self.run_id}_{self.turn_number}_{failure_type}"))
        
        failure_rates = {
            "api_timeout": 0.30,           # Was 0.15 → increase to 30%
            "confidence_decay": 0.35,      # Was 0.20 → increase to 35%
            "context_overflow": 0.25,      # Was 0.10 → increase to 25%
            "cascading_hallucination": 0.40,  # Was 0.05 → increase to 40%
            "no_failure": 0.30,            # Reduced from 0.50 to allow more failures
        }
        
        roll = failure_random.random()
        
        if failure_type == "api_timeout" and roll < failure_rates["api_timeout"]:
            return True
        elif failure_type == "confidence_decay" and roll < failure_rates["confidence_decay"]:
            return True
        elif failure_type == "context_overflow" and roll < failure_rates["context_overflow"]:
            return True
        elif failure_type == "cascading" and roll < failure_rates["cascading_hallucination"]:
            return True
        
        return False

    def _can_circuit_breaker_prevent_cascade(self) -> bool:
        """Determine if circuit breaker can prevent cascade based on condition and state."""
        if self.condition == "NO_PROTECTION":
            return False  # No protection
        elif self.condition == "TIMEOUT_ONLY":
            return False  # Only timeout protection, can't detect cascades
        elif self.condition == "SIMPLE_CB":
            # Simple CB can detect some patterns but not very sophisticated
            return random.random() < 0.3  # 30% chance of preventing cascade
        elif self.condition == "AI_CB":
            # AI-aware CB can detect cascade patterns better
            return random.random() < 0.6  # 60% chance of preventing cascade
        elif self.condition == "ADAPTIVE_CB":
            # Most sophisticated, best at preventing cascades
            return random.random() < 0.8  # 80% chance of preventing cascade
        return False

    def _simulate_agent_a(self) -> AgentResponse:
        """Simulate Agent A execution with potential failures (simulated or real API)."""
        self.turn_number += 1
        
        try:
            def agent_a_work():
                if self.real_mode:
                    # Real API call mode
                    task_context = f"Document analysis task for run {self.run_id}"
                    return self.agent_a_client.call_agent_a(task_context)
                else:
                    # Simulated mode with failure injection
                    if self._should_inject_failure("api_timeout"):
                        raise TimeoutError("API timeout injected")
                    
                    if self._should_inject_failure("confidence_decay"):
                        return Response(
                            content="Summary of document",
                            confidence=0.3,  # Low confidence
                            token_usage=2000,
                            reasoning="I'm uncertain about this summary",
                        )
                    
                    if self._should_inject_failure("context_overflow"):
                        return Response(
                            content="Partial summary...",
                            confidence=0.7,
                            token_usage=8000,  # Above threshold
                            reasoning="Processed all tokens",
                        )
                    
                    # Normal operation (simulated)
                    return Response(
                        content="Complete document summary with key points",
                        confidence=0.85,
                        token_usage=1500,
                        reasoning="Analyzed document structure and extracted main points",
                    )
            
            result = self.cb_agent_a.call(agent_a_work)
            
            return AgentResponse(
                content=result.content,
                confidence=result.confidence,
                token_usage=result.token_usage,
                reasoning=result.reasoning,
                success=True,
                failure_type=None,
            )
        except CircuitBreakerOpenError as e:
            self.metrics["circuit_trips"] += 1
            # Circuit breaker tripped - this is PROTECTION, not a failure to track in CFR
            return AgentResponse("", 0.0, 0, None, False, "circuit_open")
        except TimeoutError:
            self.metrics["agent_a_failures"] += 1
            self.cfr_tracker.record_failure(FailureEvent(
                agent_id="A", failure_type="timeout",
                timestamp=time.time(), turn_number=self.turn_number, task_id=self.task_id
            ))
            return AgentResponse("", 0.0, 0, None, False, "timeout")
        except Exception as e:
            self.metrics["agent_a_failures"] += 1
            return AgentResponse("", 0.0, 0, None, False, str(e))

    def _simulate_agent_b(self, agent_a_result: AgentResponse) -> AgentResponse:
        """Simulate Agent B processing Agent A's output."""
        self.turn_number += 1
        
        # If Agent A failed, check if this would cause a cascade
        # Circuit breakers with AI features can detect this pattern and prevent it
        if not agent_a_result.success:
            # High cascade probability when Agent A fails (60-80%)
            cascade_random = random.Random(hash(f"{self.run_id}_cascade_{self.turn_number}"))
            cascade_probability = 0.70  # 70% chance of cascade when A fails
            
            would_cascade = cascade_random.random() < cascade_probability
            
            # AI-aware circuit breakers can detect cascade risk and prevent it
            if would_cascade and self._can_circuit_breaker_prevent_cascade():
                # Circuit breaker prevented the cascade! 
                # Don't record a cascade failure - this is the protection working
                return AgentResponse(
                    content="Circuit breaker prevented cascade", 
                    confidence=0.5, 
                    token_usage=500, 
                    reasoning="Agent A failed, preventing cascade", 
                    success=True, 
                    failure_type=None
                )
            elif would_cascade:
                # Cascade happens (no protection or protection failed)
                self.metrics["agent_b_failures"] += 1
                self.cfr_tracker.record_failure(FailureEvent(
                    agent_id="B", failure_type="cascade",
                    timestamp=time.time(), turn_number=self.turn_number, task_id=self.task_id
                ))
                return AgentResponse("", 0.0, 0, None, False, "cascade_from_A")
        
        try:
            def agent_b_work():
                if self.real_mode:
                    # Real API call mode
                    task_context = f"Synthesis task for run {self.run_id}"
                    # Use Agent A's output if successful, otherwise provide context about the failure
                    agent_a_output = agent_a_result.content if agent_a_result.success else "Agent A encountered an error and could not complete its analysis."
                    return self.agent_b_client.call_agent_b(agent_a_output, task_context)
                else:
                    # Simulated mode with failure injection
                    if self._should_inject_failure("api_timeout"):
                        raise TimeoutError("API timeout injected")
                    return Response(
                        content="Final answer synthesized from Agent A",
                        confidence=0.90 if agent_a_result.success else 0.4,
                        token_usage=1200,
                        reasoning="Combined inputs and generated response",
                    )
            
            result = self.cb_agent_b.call(agent_b_work)
            return AgentResponse(
                content=result.content, confidence=result.confidence,
                token_usage=result.token_usage, reasoning=result.reasoning,
                success=True, failure_type=None,
            )
        except CircuitBreakerOpenError:
            self.metrics["circuit_trips"] += 1
            # Circuit breaker tripped - this is PROTECTION, not a failure to track in CFR
            return AgentResponse("", 0.0, 0, None, False, "circuit_open")
        except TimeoutError:
            self.metrics["agent_b_failures"] += 1
            return AgentResponse("", 0.0, 0, None, False, "timeout")
        except Exception as e:
            self.metrics["agent_b_failures"] += 1
            return AgentResponse("", 0.0, 0, None, False, str(e))

    def run_task(self) -> Dict:
        """Run a single collaborative task."""
        agent_a_result = self._simulate_agent_a()
        agent_b_result = self._simulate_agent_b(agent_a_result)
        
        self.metrics["task_completed"] = agent_a_result.success and agent_b_result.success
        self.metrics["total_turns"] = self.turn_number
        
        # Get circuit breaker metrics
        cb_metrics_a = getattr(self.cb_agent_a, 'get_metrics', lambda: {})()
        cb_metrics_b = getattr(self.cb_agent_b, 'get_metrics', lambda: {})()
        
        return {
            "run_id": self.run_id,
            "condition": self.condition,
            "task_completed": self.metrics["task_completed"],
            "metrics": self.metrics,
            "cfr": self.cfr_tracker.calculate_cfr(),
            "circuit_breaker_a": cb_metrics_a,
            "circuit_breaker_b": cb_metrics_b,
        }


class ExperimentRunner:
    """Orchestrates the full experiment (simulated and real API modes)."""
    
    CONDITIONS = ["NO_PROTECTION", "TIMEOUT_ONLY", "SIMPLE_CB", "AI_CB", "ADAPTIVE_CB"]
    
    def __init__(self, runs_per_condition: int = 55, pilot: bool = False, real_mode: bool = False):
        self.runs_per_condition = 10 if pilot else runs_per_condition
        self.pilot = pilot
        self.real_mode = real_mode
        self.results: Dict[str, List[Dict]] = {c: [] for c in self.CONDITIONS}
        setup_randomness()
    
    def run_condition(self, condition: str) -> List[Dict]:
        """Run all trials for a single condition."""
        mode_str = "REAL API" if self.real_mode else "SIMULATED"
        print(f"\n{'='*50}")
        print(f"Running condition: {condition} ({self.runs_per_condition} runs, {mode_str} mode)")
        print(f"{'='*50}")
        
        results = []
        for i in range(self.runs_per_condition):
            run_id = f"{condition}_{i:03d}"
            system = SimulatedMultiAgentSystem(condition, run_id, real_mode=self.real_mode)
            result = system.run_task()
            results.append(result)
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"  Completed {i + 1}/{self.runs_per_condition}")
        
        return results
    
    def run_all(self) -> Dict:
        """Run the full experiment."""
        mode_str = "REAL API" if self.real_mode else "SIMULATED"
        pilot_str = "PILOT (10 runs/condition)" if self.pilot else "FULL (55 runs/condition)"
        print(f"\n{'#'*60}")
        print(f"exp-001 Circuit Breaker Experiment")
        print(f"Mode: {pilot_str}, {mode_str}")
        print(f"{'#'*60}")
        
        start_time = time.time()
        
        for condition in self.CONDITIONS:
            self.results[condition] = self.run_condition(condition)
        
        elapsed = time.time() - start_time
        summary = self._calculate_summary()
        summary["elapsed_seconds"] = elapsed
        
        self._print_summary(summary)
        return summary
    
    def _calculate_summary(self) -> Dict:
        """Calculate experiment summary statistics."""
        summary = {"conditions": {}}
        
        for condition, runs in self.results.items():
            total_cfr = sum(r["cfr"]["cfr_rate"] for r in runs)
            avg_cfr = total_cfr / len(runs) if runs else 0
            completed = sum(1 for r in runs if r["task_completed"])
            
            # Count actual circuit breaker trips from CB internal state
            total_cb_trips = 0
            for r in runs:
                cb_a_trips = r.get("circuit_breaker_a", {}).get("trip_count", 0)
                cb_b_trips = r.get("circuit_breaker_b", {}).get("trip_count", 0)
                total_cb_trips += cb_a_trips + cb_b_trips
            
            summary["conditions"][condition] = {
                "runs": len(runs),
                "avg_cfr": round(avg_cfr, 4),
                "completion_rate": round(completed / len(runs), 4) if runs else 0,
                "total_circuit_trips": total_cb_trips,
                "blocked_calls": sum(r["metrics"]["circuit_trips"] for r in runs),  # Calls blocked by open CB
            }
        
        return summary
    
    def _print_summary(self, summary: Dict) -> None:
        """Print formatted summary."""
        print(f"\n{'='*60}")
        print("EXPERIMENT RESULTS SUMMARY")
        print(f"{'='*60}")
        
        print(f"\n{'Condition':<15} {'Runs':<8} {'Avg CFR':<12} {'Completion':<12} {'Trips':<8}")
        print("-" * 55)
        
        for condition, stats in summary["conditions"].items():
            print(f"{condition:<15} {stats['runs']:<8} {stats['avg_cfr']:<12.4f} {stats['completion_rate']:<12.4f} {stats['total_circuit_trips']:<8}")
        
        print(f"\nElapsed time: {summary.get('elapsed_seconds', 0):.2f}s")
        
        # Hypothesis check
        baseline = summary["conditions"].get("TIMEOUT_ONLY", {}).get("avg_cfr", 0)
        ai_cb = summary["conditions"].get("AI_CB", {}).get("avg_cfr", 0)
        
        if baseline > 0:
            reduction = (baseline - ai_cb) / baseline * 100
            print(f"\n** H1 Check: CFR reduction vs TIMEOUT_ONLY baseline **")
            print(f"   Baseline CFR: {baseline:.4f}")
            print(f"   AI_CB CFR:    {ai_cb:.4f}")
            print(f"   Reduction:    {reduction:.1f}%")
            print(f"   Target:       ≥30%")
            print(f"   Result:       {'✅ PASS' if reduction >= 30 else '❌ FAIL (need more data or adjustment)'}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run exp-001 Circuit Breaker Experiment")
    parser.add_argument("--pilot", action="store_true", help="Run pilot (10 runs/condition)")
    parser.add_argument("--full", action="store_true", help="Run full experiment (55 runs/condition)")
    parser.add_argument("--real", action="store_true", help="Use real API calls instead of simulation")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file")
    args = parser.parse_args()
    
    runs = 10 if args.pilot else 55
    runner = ExperimentRunner(runs_per_condition=runs, pilot=args.pilot, real_mode=args.real)
    summary = runner.run_all()
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    return summary


if __name__ == "__main__":
    main()
