#!/usr/bin/env python3
"""
Quick test to verify circuit breaker functionality
"""
from circuit_breaker import AIAdaptiveCircuitBreaker, CircuitConfig, Response, CircuitBreakerOpenError

def test_ai_circuit_breaker():
    """Test that AI circuit breaker trips on low confidence."""
    config = CircuitConfig(
        confidence_threshold=0.6,  # Should trip if confidence < 0.6
        failure_threshold=2,       # Trip after 2 failures
    )
    
    cb = AIAdaptiveCircuitBreaker(config)
    
    def mock_low_confidence_call():
        """Mock call that returns low confidence."""
        return Response(
            content="Uncertain response",
            confidence=0.3,  # Below threshold of 0.6
            token_usage=1000,
            reasoning="Not sure about this"
        )
    
    def mock_high_confidence_call():
        """Mock call that returns high confidence."""
        return Response(
            content="Confident response", 
            confidence=0.8,  # Above threshold
            token_usage=1000,
            reasoning="Very sure about this"
        )
    
    print("Testing AI Circuit Breaker...")
    print(f"Initial state: {cb.state}")
    
    # First low confidence call - should work but increment failure count
    try:
        result1 = cb.call(mock_low_confidence_call)
        print(f"Call 1: confidence={result1.confidence}, failures={cb.consecutive_failures}")
    except CircuitBreakerOpenError:
        print("Call 1: Circuit breaker opened early!")
    
    # Second low confidence call - should trip the circuit
    try:
        result2 = cb.call(mock_low_confidence_call)
        print(f"Call 2: confidence={result2.confidence}, failures={cb.consecutive_failures}")
    except CircuitBreakerOpenError:
        print("Call 2: Circuit breaker opened!")
    
    # Third call - should be blocked
    try:
        result3 = cb.call(mock_high_confidence_call)
        print(f"Call 3: Should not execute - circuit is open")
    except CircuitBreakerOpenError:
        print("Call 3: Correctly blocked by open circuit!")
    
    print(f"Final state: {cb.state}")
    print(f"Total trips: {len(cb.trip_log)}")
    print(f"Metrics: {cb.get_metrics()}")
    
    return cb.consecutive_failures >= 2

if __name__ == "__main__":
    success = test_ai_circuit_breaker()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")