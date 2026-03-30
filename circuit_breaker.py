"""
Circuit Breaker Implementations for exp-001
Based on DIAMOND/RESEARCH/experiments/exp-001-circuit-breaker-DESIGN.md
"""
from enum import Enum, auto
from config import CircuitBreakerConfig

class ExperimentResult:
    def __init__(self, agent_chain_length, cfr):
        self.agent_chain_length = agent_chain_length
        self.cfr = cfr
from typing import Optional, List, Dict, Any
import time
import random
import json


class CircuitState(Enum):
    REASONING_CLOSED = auto()
    REASONING_OPEN = auto()
    CONTEXT_OPEN = auto()
    CONFIDENCE_HALF_OPEN = auto()


class CircuitConfig:
    """Configuration for circuit breaker thresholds."""
    def __init__(
        self,
        confidence_threshold: float = 0.5,
        context_threshold: int = 6000,
        predictability_min: float = 0.3,
        failure_threshold: int = 3,
        timeout_seconds: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        self.confidence_threshold = confidence_threshold
        self.context_threshold = context_threshold
        self.predictability_min = predictability_min
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls


class Response:
    """Agent response wrapper."""
    def __init__(
        self,
        content: str,
        confidence: float,
        token_usage: int,
        reasoning: Optional[str] = None,
    ):
        self.content = content
        self.confidence = confidence
        self.token_usage = token_usage
        self.reasoning = reasoning


class ReliabilityTracker:
    """Princeton-inspired reliability metrics tracker."""
    def __init__(self):
        self.consistency_history: List[bool] = []
        self.failure_history: List[Dict] = []
        self.predictability_scores: List[float] = []
        self.safety_events: List[Dict] = []

    def record_consistency(self, is_consistent: bool) -> None:
        """Record ℛCon (consistency) metric."""
        self.consistency_history.append(is_consistent)

    def record_failure(self, timestamp: float, severity: str) -> None:
        """Record ℛRob (robustness) metric."""
        self.failure_history.append({
            "timestamp": timestamp,
            "severity": severity,
        })

    def update_predictability(self, score: float) -> None:
        """Record ℛPre (predictability) metric."""
        self.predictability_scores.append(score)

    def record_safety_event(self, event_type: str, recovered: bool) -> None:
        """Record ℛSaf (safety/corrigibility) metric."""
        self.safety_events.append({
            "type": event_type,
            "recovered": recovered,
            "timestamp": time.time(),
        })


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class AIAdaptiveCircuitBreaker:
    """
    Four-state circuit breaker with Princeton-inspired metrics.
    States:
    - REASONING_CLOSED: Normal operation, full monitoring
    - REASONING_OPEN: Failure detected, rejecting requests
    - CONTEXT_OPEN: Token exhaustion risk, rejecting large requests
    - CONFIDENCE_HALF_OPEN: Testing recovery with limited traffic
    """
    def __init__(self, config: CircuitConfig):
        self.run_experiments(config)

    def run_progressive_chain_experiments(self, config: CircuitBreakerConfig):
        """Run progressive chain experiments for 2→3→4→5→6 agents."""
        results = []
        progressive_lengths = range(2, 7)
        for length in progressive_lengths:
            failures = 0
            total_calls = 100  # Example total calls per test
            for _ in range(total_calls):
                if self.simulate_agent_chain(length):
                    failures += 1
            cfr = failures / total_calls
            results.append(ExperimentResult(length, cfr))
        return results

    def run_experiments(self, config: CircuitBreakerConfig):
        """Run experiments with different agent chain lengths and calculate CFR."""
        results = []
        for length in config.test_lengths:
            failures = 0
            total_calls = 100  # Example total calls per test
            for _ in range(total_calls):
                if self.simulate_agent_chain(length):
                    failures += 1
            cfr = failures / total_calls
            results.append(ExperimentResult(length, cfr))
        self.print_results(results)

    @staticmethod
    def simulate_agent_chain(length):
        """Simulate an agent chain of the given length and introduce failures."""
        failure_occurred = False
        for _ in range(length):
            if random.random() < 0.1:  # Example failure injection rate
                failure_occurred = True
                break
        return failure_occurred

    @staticmethod
    def print_results(results):
        print("CFR Results:")
        print("Length | CFR")
        for result in results:
            print(f"{result.agent_chain_length}      | {result.cfr:.2f}")


        self.config = config
        self.state = CircuitState.REASONING_CLOSED
        self.reliability_metrics = ReliabilityTracker()
        
        # Princeton framework dimensions
        self.consistency_buffer: List[bool] = []  # ℛCon
        self.robustness_score: float = 1.0  # ℛRob
        self.predictability_estimate: float = 0.0  # ℛPre
        self.safety_score: float = 1.0  # ℛSaf
        
        # Failure tracking
        self.consecutive_failures = 0
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state_entry_time = time.time()
        self.half_open_calls_allowed = config.half_open_max_calls
        
        # Metrics logging
        self.trip_log: List[Dict] = []

    def is_reasoning_consistent(self, response: Response) -> bool:
        """Check if reasoning is consistent with output (ℛCon)."""
        if not response.reasoning:
            return True  # No reasoning to check
        
        # Check for obvious contradictions
        reasoning_lower = response.reasoning.lower()
        content_lower = response.content.lower()
        
        # Simple heuristic: check if key claims align
        contradiction_markers = [
            "i don't know" in reasoning_lower and "here is" in content_lower,
            "uncertain" in reasoning_lower and "definitely" in content_lower,
            "low confidence" in reasoning_lower and "high confidence" in content_lower,
        ]
        is_consistent = not any(contradiction_markers)
        self.consistency_buffer.append(is_consistent)
        
        # Keep buffer bounded
        if len(self.consistency_buffer) > 10:
            self.consistency_buffer.pop(0)
        
        return is_consistent

    def calculate_predictability(self, response: Response) -> float:
        """Calculate trajectory predictability score (ℛPre)."""
        # Base predictability on confidence and token usage
        confidence_score = response.confidence
        usage_ratio = response.token_usage / self.config.context_threshold
        
        # More predictable = higher confidence, lower token usage
        predictability = confidence_score * (1 - usage_ratio * 0.5)
        predictability = max(0.0, min(1.0, predictability))
        self.predictability_estimate = predictability
        return predictability

    def transition_to(self, new_state: CircuitState) -> None:
        """Handle state transition with logging."""
        old_state = self.state
        self.state = new_state
        self.state_entry_time = time.time()
        
        self.trip_log.append({
            "timestamp": time.time(),
            "from": old_state.name,
            "to": new_state.name,
        })
        
        if new_state == CircuitState.CONFIDENCE_HALF_OPEN:
            self.half_open_calls_allowed = self.config.half_open_max_calls

    def should_trip(self, agent_response: Response) -> bool:
        """Multi-dimensional trip detection."""
        # ℛCon: Consistency check
        if not self.is_reasoning_consistent(agent_response):
            self.reliability_metrics.record_consistency(False)
            return True
        self.reliability_metrics.record_consistency(True)
        
        # ℛRob: Fault detection via confidence
        if agent_response.confidence < self.config.confidence_threshold:
            self.reliability_metrics.record_failure(
                time.time(), "confidence_threshold"
            )
            return True
        
        # Context limit (token exhaustion)
        if agent_response.token_usage > self.config.context_threshold:
            return True
        
        # ℛPre: Trajectory predictability
        predictability = self.calculate_predictability(agent_response)
        if predictability < self.config.predictability_min:
            return True
        
        return False

    def call(self, func, *args, **kwargs):
        """Execute a call with circuit breaker protection."""
        if self.state == CircuitState.REASONING_OPEN:
            # Check if we can attempt recovery
            if self.can_attempt_recovery():
                self.attempt_recovery()
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN (REASONING_OPEN)")
        
        if self.state == CircuitState.CONTEXT_OPEN:
            # Check token estimate before allowing
            estimated_tokens = kwargs.get('estimated_tokens', 0)
            if estimated_tokens > self.config.context_threshold * 0.5:
                raise CircuitBreakerOpenError("Context limit protection")
        
        if self.state == CircuitState.CONFIDENCE_HALF_OPEN:
            if self.half_open_calls_allowed <= 0:
                raise CircuitBreakerOpenError("Half-open quota exceeded")
            self.half_open_calls_allowed -= 1
        
        try:
            result = func(*args, **kwargs)
            
            # Check if result should trip circuit
            if isinstance(result, Response) and self.should_trip(result):
                self.consecutive_failures += 1
                self.failure_count += 1
                self.last_failure_time = time.time()
                self.reliability_metrics.record_failure(time.time(), "response_quality")
                
                if self.consecutive_failures >= self.config.failure_threshold:
                    self.transition_to(CircuitState.REASONING_OPEN)
                    self._schedule_recovery_test()
                    # Don't raise here - let the bad response through but circuit is now open
            else:
                # Success - reset failure counter
                if self.consecutive_failures > 0:
                    self.consecutive_failures = 0
                
                # If in half-open, transition to closed on success
                if self.state == CircuitState.CONFIDENCE_HALF_OPEN:
                    self.transition_to(CircuitState.REASONING_CLOSED)
            
            return result
            
        except Exception as e:
            self.consecutive_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.reliability_metrics.record_failure(time.time(), "exception")
            
            if self.consecutive_failures >= self.config.failure_threshold:
                self.transition_to(CircuitState.REASONING_OPEN)
                self._schedule_recovery_test()
            raise

    def _schedule_recovery_test(self) -> None:
        """Schedule periodic recovery attempts (simplified)."""
        self.last_failure_time = time.time()

    def can_attempt_recovery(self) -> bool:
        """Check if enough time has passed for recovery attempt."""
        if self.state != CircuitState.REASONING_OPEN:
            return False
        if self.last_failure_time is None:
            return True
        elapsed = time.time() - self.last_failure_time
        return elapsed > self.config.timeout_seconds

    def attempt_recovery(self) -> None:
        """Transition to half-open to test recovery."""
        if self.can_attempt_recovery():
            self.transition_to(CircuitState.CONFIDENCE_HALF_OPEN)

    def get_metrics(self) -> dict:
        """Return current reliability metrics."""
        return {
            "RCon_consistency_rate": sum(self.consistency_buffer) / len(self.consistency_buffer) if self.consistency_buffer else 1.0,
            "RRob_failure_count": self.failure_count,
            "RPre_predictability": self.predictability_estimate,
            "RSaf_recovery_attempts": len([e for e in self.reliability_metrics.safety_events if e["type"] == "recovery"]),
            "state": self.state.name,
            "consecutive_failures": self.consecutive_failures,
            "trip_log": self.trip_log,
            "trip_count": len(self.trip_log),
        }


class SimpleCircuitBreaker:
    """Traditional two-state circuit breaker for comparison."""
    def __init__(self, failure_threshold: int = 3, timeout_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.consecutive_failures = 0
        self.is_open = False
        self.last_failure_time: Optional[float] = None
        self.trip_count = 0
        self.recovery_count = 0

    def call(self, func, *args, **kwargs):
        """Execute with simple circuit breaker protection."""
        if self.is_open:
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed > self.timeout_seconds:
                    self.is_open = False
                    self.consecutive_failures = 0
                    self.recovery_count += 1
                else:
                    raise CircuitBreakerOpenError("Circuit OPEN")
        
        try:
            result = func(*args, **kwargs)
            
            # Check if response indicates failure (low confidence, etc.)
            if isinstance(result, Response):
                if result.confidence < 0.5:  # Consider low confidence as failure
                    self.consecutive_failures += 1
                    self.last_failure_time = time.time()
                    if self.consecutive_failures >= self.failure_threshold:
                        self.is_open = True
                        self.trip_count += 1
                else:
                    self.consecutive_failures = 0
            else:
                self.consecutive_failures = 0
            
            return result
        except Exception:
            self.consecutive_failures += 1
            self.last_failure_time = time.time()
            if self.consecutive_failures >= self.failure_threshold:
                self.is_open = True
                self.trip_count += 1
            raise

    def get_metrics(self) -> dict:
        return {
            "state": "OPEN" if self.is_open else "CLOSED",
            "trip_count": self.trip_count,
            "recovery_count": self.recovery_count,
            "consecutive_failures": self.consecutive_failures,
        }


class TimeoutOnlyProtection:
    """HTTP timeout only - production baseline."""
    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0

    def call(self, func, *args, **kwargs):
        """Execute with timeout only."""
        # In production, would use asyncio.timeout
        return func(*args, **kwargs)

    def get_metrics(self) -> dict:
        return {
            "state": "TIMEOUT_ONLY",
            "timeout_seconds": self.timeout_seconds,
            "failure_count": self.failure_count,
        }


class NoProtection:
    """No circuit breaker at all - absolute baseline."""
    def __init__(self):
        self.call_count = 0

    def call(self, func, *args, **kwargs):
        """Execute without protection."""
        self.call_count += 1
        return func(*args, **kwargs)

    def get_metrics(self) -> dict:
        return {
            "state": "NO_PROTECTION",
            "call_count": self.call_count,
        }
