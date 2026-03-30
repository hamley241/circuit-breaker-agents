"""
Test script to validate real API integration for exp-001.
Tests both simulated and real modes (if API keys are available).
"""
import os
import sys
from pathlib import Path

# Add current directory to path
HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))

def test_simulated_mode():
    """Test that simulated mode still works."""
    print("Testing simulated mode...")
    
    from experiment_runner import SimulatedMultiAgentSystem
    
    # Test simulated mode
    system = SimulatedMultiAgentSystem("AI_CB", "test_sim_001", real_mode=False)
    result = system.run_task()
    
    assert "run_id" in result
    assert "condition" in result
    assert "task_completed" in result
    assert result["condition"] == "AI_CB"
    
    print("✅ Simulated mode test passed")


def test_real_mode_availability():
    """Test if real mode dependencies are available."""
    print("Testing real mode availability...")
    
    try:
        from api_clients import APIClientFactory, APIConfig
        print("✅ API clients imported successfully")
        
        # Test if environment variables are set
        has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
        has_anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
        
        print(f"OpenAI API Key available: {has_openai_key}")
        print(f"Anthropic API Key available: {has_anthropic_key}")
        
        if has_openai_key and has_anthropic_key:
            print("✅ Real mode should work (API keys available)")
            return True
        else:
            print("⚠️ Real mode will not work (missing API keys)")
            return False
            
    except ImportError as e:
        print(f"❌ API clients not available: {e}")
        return False


def test_real_mode_integration():
    """Test real mode integration (if API keys are available)."""
    print("Testing real mode integration...")
    
    if not test_real_mode_availability():
        print("Skipping real mode test (dependencies not available)")
        return
    
    from experiment_runner import SimulatedMultiAgentSystem
    
    try:
        # Test real mode
        system = SimulatedMultiAgentSystem("SIMPLE_CB", "test_real_001", real_mode=True)
        print("✅ Real mode system created successfully")
        
        # Note: We won't run the full task to avoid API costs during testing
        # Just verify the system was created without errors
        print("✅ Real mode integration test passed (system creation)")
        
    except Exception as e:
        print(f"❌ Real mode integration test failed: {e}")
        raise


def test_experiment_runner_integration():
    """Test ExperimentRunner with real_mode parameter."""
    print("Testing ExperimentRunner integration...")
    
    from experiment_runner import ExperimentRunner
    
    # Test simulated mode
    runner_sim = ExperimentRunner(runs_per_condition=1, pilot=True, real_mode=False)
    assert runner_sim.real_mode == False
    print("✅ ExperimentRunner simulated mode created")
    
    # Test real mode (just creation, not execution)
    runner_real = ExperimentRunner(runs_per_condition=1, pilot=True, real_mode=True)
    assert runner_real.real_mode == True
    print("✅ ExperimentRunner real mode created")


def test_modal_app_integration():
    """Test Modal app parameter passing."""
    print("Testing Modal app integration...")
    
    # Import the modal app module
    try:
        import modal_app
        print("✅ Modal app imported successfully")
        
        # Check if the function signature includes real_mode
        import inspect
        sig = inspect.signature(modal_app.run_experiment)
        params = list(sig.parameters.keys())
        
        assert "real_mode" in params, "real_mode parameter missing from run_experiment"
        print("✅ Modal app has real_mode parameter")
        
    except ImportError as e:
        if "modal" in str(e):
            print("⚠️ Modal not available locally (expected - runs in Modal environment)")
            print("✅ Modal app integration test skipped")
        else:
            print(f"❌ Modal app integration test failed: {e}")
            raise
    except Exception as e:
        print(f"❌ Modal app integration test failed: {e}")
        raise


def main():
    """Run all integration tests."""
    print("🧪 Running exp-001 real API integration tests...\n")
    
    try:
        test_simulated_mode()
        print()
        
        test_real_mode_availability()
        print()
        
        test_real_mode_integration()
        print()
        
        test_experiment_runner_integration()
        print()
        
        test_modal_app_integration()
        print()
        
        print("🎉 All integration tests passed!")
        print("\nUsage examples:")
        print("  Simulated mode: python experiment_runner.py --pilot")
        print("  Real API mode:  python experiment_runner.py --pilot --real")
        print("  Modal simulated: modal run modal_app.py::main --runs 5")
        print("  Modal real API:  modal run modal_app.py::main --runs 5 --real")
        
    except Exception as e:
        print(f"\n❌ Integration tests failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()