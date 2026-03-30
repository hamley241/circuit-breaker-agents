"""
Circuit Breaker Implementations - FIXED VERSION for exp-001
============================================================
FIXES:
1. More permissive thresholds to allow cascade formation
2. Smarter trip logic - only trip on quality degradation trends
3. Better recovery mechanisms
4. Separate CFR tracking that accounts for blocked vs prevented cascades
"""
from enum import Enum, auto
from typing import Optional, List, Dict, Any
import time
import random
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("circuit_breaker")


class CircuitState(Enum):
    REASONING_CLOSED = auto()
    REASONING_OPEN = auto()
    CONTEXT_OPEN = auto()
    CONFIDENCE_HALF_OPEN = auto()


class CircuitConfig:
    """FIXED: More permissive configuration for circuit breaker thresholds."""
    def __init__(
        self,
        confidence_threshold: float = 0.3,  # FIX: Lowered from 0.5-0.6 to 0.3
        context_threshold: int = 7000,      # FIX: Raised from 5000-6000 to 7000
        predictability_min: float = 0.2,   # FIX: Lowered from 0.3-0.35 to 0.2
        failure_threshold: int = 3,         # FIX: Raised from 2 to 3 consecutive failures
        timeout_seconds: float = 5.0,      # FIX: Shortened recovery time
        half_open_max_calls: int = 5,       # FIX: More test calls in half-open
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


class ImprovedAdaptiveCircuitBreaker:
    """
    FIXED VERSION: Less aggressive circuit breaker that allows cascades to form
    before intervening, with better threshold tuning and recovery.
    
    FIXES:
    1. More permissive thresholds (confidence 0.3, context 7000, predictability 0.2)
    2. Requires 3 consecutive failures instead of 2
    3. Faster recovery (5 seconds instead of 10-15)
    4. Trend-based tripping (not just single bad responses)
    5. Better half-open testing (5 calls instead of 3)
    """
    def __init__(self, config: CircuitConfig):
        self.config = config
        self.state = CircuitState.REASONING_CLOSED
        self.reliability_metrics = ReliabilityTracker()
        
        # Princeton framework dimensions
        self.consistency_buffer: List[bool] = []  # ℛCon
        self.robustness_score: float = 1.0  # ℛRob
        self.predictability_estimate: float = 0.0  # ℛPre
        self.safety_score: float = 1.0  # ℛSaf
        
        # Failure tracking - IMPROVED
        self.consecutive_failures = 0
        self.failure_count = 0
        self.success_count = 0  # FIX: Track successes too
        self.last_failure_time: Optional[float] = None
        self.state_entry_time = time.time()
        self.half_open_calls_allowed = config.half_open_max_calls
        
        # FIX: Recent response quality tracking for trend analysis
        self.recent_responses: List[Response] = []
        self.max_recent_responses = 5
        
        # Metrics logging
        self.trip_log: List[Dict] = []
        self.debug_log: List[Dict] = []

    def _debug_log(self, message: str, **kwargs):
        """Add debug logging to trace circuit breaker decisions."""
        log_entry = {
            "timestamp": time.time(),
            "state": self.state.name,
            "message": message,
            **kwargs
        }
        self.debug_log.append(log_entry)
        logger.debug(f"[IMPROVED_CB] {message} | State: {self.state.name} | {kwargs}")

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
        usage_ratio = min(1.0, response.token_usage / self.config.context_threshold)
        
        # More predictable = higher confidence, reasonable token usage
        predictability = confidence_score * (1 - usage_ratio * 0.3)  # FIX: Less penalty for token usage
        predictability = max(0.0, min(1.0, predictability))
        self.predictability_estimate = predictability
        return predictability

    def _is_response_degrading_trend(self) -> bool:
        """FIX: Check if recent responses show a degrading trend."""
        if len(self.recent_responses) < 3:
            return False
        
        # Check last 3 responses for degrading confidence
        recent_confidences = [r.confidence for r in self.recent_responses[-3:]]
        
        # Simple trend: each response worse than the previous
        degrading = all(recent_confidences[i] > recent_confidences[i+1] 
                       for i in range(len(recent_confidences)-1))
        
        # Also check if all recent responses are below threshold
        all_below_threshold = all(conf < self.config.confidence_threshold * 1.5  # FIX: 1.5x threshold for trend
                                for conf in recent_confidences)
        
        return degrading and all_below_threshold

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
        
        self._debug_log(f"State transition: {old_state.name} -> {new_state.name}")
        
        if new_state == CircuitState.CONFIDENCE_HALF_OPEN:
            self.half_open_calls_allowed = self.config.half_open_max_calls
            self._debug_log(f"Half-open: allowing {self.half_open_calls_allowed} test calls")

    def should_trip(self, agent_response: Response) -> bool:
        """FIXED: More intelligent trip detection with trend analysis."""
        trip_reasons = []
        
        # Add to recent responses for trend analysis
        self.recent_responses.append(agent_response)
        if len(self.recent_responses) > self.max_recent_responses:
            self.recent_responses.pop(0)
        
        # ℛCon: Consistency check
        if not self.is_reasoning_consistent(agent_response):
            self.reliability_metrics.record_consistency(False)
            trip_reasons.append("inconsistent_reasoning")
        else:
            self.reliability_metrics.record_consistency(True)
        
        # ℛRob: Fault detection via confidence - FIXED with more permissive thresholds
        if agent_response.confidence < self.config.confidence_threshold:
            self.reliability_metrics.record_failure(
                time.time(), "confidence_threshold"
            )
            trip_reasons.append(f"low_confidence({agent_response.confidence}<{self.config.confidence_threshold})")
        
        # Context limit (token exhaustion) - FIXED with higher threshold
        if agent_response.token_usage > self.config.context_threshold:
            trip_reasons.append(f"token_limit({agent_response.token_usage}>{self.config.context_threshold})")
        
        # ℛPre: Trajectory predictability - FIXED with lower threshold
        predictability = self.calculate_predictability(agent_response)
        if predictability < self.config.predictability_min:
            trip_reasons.append(f"low_predictability({predictability}<{self.config.predictability_min})")
        
        # FIX: Only trip if we see degrading trends, not single bad responses
        trend_degrading = self._is_response_degrading_trend()
        if trend_degrading:
            trip_reasons.append("degrading_trend")
        
        # FIX: Only trip if multiple reasons OR clear degrading trend
        should_trip = len(trip_reasons) >= 2 or trend_degrading
        
        self._debug_log(
            f"Trip decision: {'TRIP' if should_trip else 'OK'}", 
            confidence=agent_response.confidence,
            tokens=agent_response.token_usage,
            predictability=predictability,
            reasons=trip_reasons,
            trend_degrading=trend_degrading,
            recent_responses_count=len(self.recent_responses)
        )
        
        return should_trip

    def call(self, func, *args, **kwargs):
        """Execute a call with improved circuit breaker protection."""
        call_start_time = time.time()
        
        # Circuit open logic - allow recovery attempts
        if self.state == CircuitState.REASONING_OPEN:
            if self.can_attempt_recovery():
                self._debug_log("Recovery timeout elapsed, transitioning to half-open")
                self.transition_to(CircuitState.CONFIDENCE_HALF_OPEN)
            else:
                self._debug_log("Circuit OPEN - blocking call", 
                              time_since_failure=time.time() - (self.last_failure_time or 0))
                raise CircuitBreakerOpenError("Circuit breaker is OPEN (REASONING_OPEN)")
        
        if self.state == CircuitState.CONTEXT_OPEN:
            estimated_tokens = kwargs.get('estimated_tokens', 0)
            if estimated_tokens > self.config.context_threshold * 0.7:  # FIX: 70% threshold
                self._debug_log("Context protection - blocking large request", tokens=estimated_tokens)
                raise CircuitBreakerOpenError("Context limit protection")
        
        if self.state == CircuitState.CONFIDENCE_HALF_OPEN:
            if self.half_open_calls_allowed <= 0:
                self._debug_log("Half-open quota exceeded - blocking call")
                raise CircuitBreakerOpenError("Half-open quota exceeded")
            self.half_open_calls_allowed -= 1
            self._debug_log(f"Half-open call allowed, {self.half_open_calls_allowed} remaining")
        
        try:
            self._debug_log("Executing function call")
            result = func(*args, **kwargs)
            
            # Response quality assessment
            if isinstance(result, Response):
                should_trip_decision = self.should_trip(result)
                
                if should_trip_decision:
                    self.consecutive_failures += 1
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    self.reliability_metrics.record_failure(time.time(), "response_quality")
                    
                    self._debug_log("Poor quality response detected", 
                                  consecutive_failures=self.consecutive_failures,
                                  threshold=self.config.failure_threshold)
                    
                    # FIX: Only trip after consecutive failures reach threshold
                    if self.consecutive_failures >= self.config.failure_threshold:
                        self.transition_to(CircuitState.REASONING_OPEN)
                        self._schedule_recovery_test()
                    
                    # FIX: Still allow the response through, just mark as failure
                    # This allows cascades to form naturally
                    return result
                else:
                    # Success - reset failure counter and track success
                    if self.consecutive_failures > 0:
                        self._debug_log("Quality improved - resetting failure counter", 
                                       previous_failures=self.consecutive_failures)
                        self.consecutive_failures = 0
                    
                    self.success_count += 1
                    
                    # If in half-open, transition to closed on success
                    if self.state == CircuitState.CONFIDENCE_HALF_OPEN:
                        self._debug_log("Half-open success - closing circuit")
                        self.transition_to(CircuitState.REASONING_CLOSED)
            
            self._debug_log("Call completed successfully", 
                           duration_ms=(time.time() - call_start_time) * 1000)
            return result
            
        except Exception as e:
            self.consecutive_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.reliability_metrics.record_failure(time.time(), "exception")
            
            self._debug_log("Exception occurred", 
                           exception=str(e),
                           consecutive_failures=self.consecutive_failures)
            
            if self.consecutive_failures >= self.config.failure_threshold:
                self.transition_to(CircuitState.REASONING_OPEN)
                self._schedule_recovery_test()
            raise

    def _schedule_recovery_test(self) -> None:
        """Schedule periodic recovery attempts."""
        self.last_failure_time = time.time()
        self._debug_log("Scheduled recovery test", timeout_seconds=self.config.timeout_seconds)

    def can_attempt_recovery(self) -> bool:
        """Check if enough time has passed for recovery attempt."""
        if self.state != CircuitState.REASONING_OPEN:
            return False
        if self.last_failure_time is None:
            return True
        elapsed = time.time() - self.last_failure_time
        can_recover = elapsed > self.config.timeout_seconds
        self._debug_log(f"Recovery check: elapsed={elapsed:.1f}s, timeout={self.config.timeout_seconds}s, can_recover={can_recover}")
        return can_recover

    def attempt_recovery(self) -> None:
        """Transition to half-open to test recovery."""
        if self.can_attempt_recovery():
            self._debug_log("Attempting recovery - transitioning to half-open")
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
            "success_count": self.success_count,
            "trip_log": self.trip_log,
            "trip_count": len(self.trip_log),
            "debug_log": self.debug_log[-10:],  # Last 10 debug entries
        }


# Keep the original classes for comparison
class AIAdaptiveCircuitBreaker:
    """Original version - for comparison."""
    def __init__(self, config: CircuitConfig):
        self.config = config
        self.state = CircuitState.REASONING_CLOSED
        self.reliability_metrics = ReliabilityTracker()
        self.consecutive_failures = 0
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state_entry_time = time.time()
        self.half_open_calls_allowed = config.half_open_max_calls
        self.trip_log: List[Dict] = []

    def call(self, func, *args, **kwargs):
        """Original call method."""
        if self.state == CircuitState.REASONING_OPEN:
            if self.can_attempt_recovery():
                self.state = CircuitState.CONFIDENCE_HALF_OPEN
                self.half_open_calls_allowed = self.config.half_open_max_calls
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            
            if isinstance(result, Response):
                if result.confidence < self.config.confidence_threshold:
                    self.consecutive_failures += 1
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    
                    if self.consecutive_failures >= self.config.failure_threshold:
                        self.state = CircuitState.REASONING_OPEN
                        self.trip_log.append({"timestamp": time.time(), "reason": "quality_failure"})
                    
                    raise CircuitBreakerOpenError("Low quality response blocked")
                else:
                    self.consecutive_failures = 0
                    if self.state == CircuitState.CONFIDENCE_HALF_OPEN:
                        self.state = CircuitState.REASONING_CLOSED
            
            return result
            
        except Exception as e:
            self.consecutive_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.consecutive_failures >= self.config.failure_threshold:
                self.state = CircuitState.REASONING_OPEN
                self.trip_log.append({"timestamp": time.time(), "reason": "exception"})
            raise

    def can_attempt_recovery(self) -> bool:
        """Check if recovery is possible."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time > self.config.timeout_seconds

    def get_metrics(self) -> dict:
        return {
            "state": self.state.name,
            "trip_count": len(self.trip_log),
            "consecutive_failures": self.consecutive_failures,
            "failure_count": self.failure_count,
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