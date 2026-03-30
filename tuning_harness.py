#!/usr/bin/env python3
"""
Automated Tuning Harness for exp-001b Circuit Breaker Simulator

Systematically sweeps failure profile parameters (Stage 1) and circuit breaker 
thresholds (Stage 2) to find configurations where breakers trip mid-run and 
recovery mechanisms execute successfully.

Usage:
    python3 tuning_harness.py --stage failure    # Stage 1: Failure profile tuning
    python3 tuning_harness.py --stage breaker    # Stage 2: Circuit breaker tuning  
    python3 tuning_harness.py --resume          # Resume from last checkpoint
    python3 tuning_harness.py --dry-run         # Show parameter grid without running

Key Features:
- Two-stage parameter search (failure profiles first, then breaker thresholds)
- Small batch execution with configurable runs per condition
- Comprehensive metric logging to results/tuning/tuning-log.jsonl
- Resume capability via checkpoint files
- Modular design for future Bayesian/advanced search strategies

Example Output Metrics:
- Average trip turn (target: 6-10)
- Recovery attempt percentage  
- Run completion percentage
- Token consumption patterns
- Cascading failure rate (CFR)
"""

import os
import sys
import json
import time
import argparse
import itertools
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, NamedTuple
from dataclasses import dataclass, asdict
from datetime import datetime

# Add current directory to path for simulator imports
sys.path.insert(0, str(Path(__file__).parent))

from simulator import SimulatorConfig, CFRTracker, SimulatorRunner, SimulatedMultiAgentSystem
from circuit_breaker import CircuitConfig, AIAdaptiveCircuitBreaker


class ParameterSet(NamedTuple):
    """Represents a single parameter combination to test."""
    stage: str  # "failure" or "breaker"
    params: Dict[str, Any]
    run_id: str  # unique identifier


@dataclass
@dataclass
class TuningResult:
    """Results from a single parameter set evaluation."""
    parameter_set: ParameterSet
    timestamp: str
    metrics: Dict[str, Any]
    runs_completed: int
    runs_attempted: int
    success: bool
    error_message: Optional[str] = None


class CustomCircuitBreakerSystem(SimulatedMultiAgentSystem):
    """Extended system that can use custom circuit breaker configs."""
    
    def __init__(self, config: SimulatorConfig, run_id: str, custom_circuit_config: Optional[CircuitConfig] = None):
        super().__init__(config, run_id)
        self.custom_circuit_config = custom_circuit_config
    
    def _create_protection(self):
        """Create circuit breaker with custom config if provided."""
        if self.custom_circuit_config and self.config.condition == "AI_CB":
            return AIAdaptiveCircuitBreaker(self.custom_circuit_config)
        else:
            # Fall back to parent implementation
            return super()._create_protection()


class TuningSimulatorRunner(SimulatorRunner):
    """Extended runner that supports custom circuit breaker configs."""
    
    def __init__(self, config: SimulatorConfig, custom_circuit_config: Optional[CircuitConfig] = None):
        super().__init__(config)
        self.custom_circuit_config = custom_circuit_config
    
    def run_all(self) -> Dict:
        """Run simulation with optional custom circuit config."""
        print(f"\n{'='*60}")
        print(f"exp-001b Tuning Harness - {self.config.condition}")
        print(f"Workload: {self.config.workload} | Runs: {self.config.runs} | Seed: {self.config.seed}")
        if self.custom_circuit_config:
            print(f"Custom Circuit Config: failure_threshold={self.custom_circuit_config.failure_threshold}, timeout={self.custom_circuit_config.timeout_seconds}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        for i in range(self.config.runs):
            run_id = f"{self.config.condition}_{self.config.workload}_{i:03d}"
            
            if self.config.verbose:
                print(f"\nRun {i+1}/{self.config.runs}: {run_id}")
            
            # Use custom system if we have custom circuit config
            system = CustomCircuitBreakerSystem(self.config, run_id, self.custom_circuit_config)
            result = system.run_task()
            self.results.append(result)
            
            # Progress indicator
            if not self.config.verbose and (i + 1) % 5 == 0:
                print(f"  Completed {i + 1}/{self.config.runs}")
        
        elapsed = time.time() - start_time
        summary = self._calculate_summary()
        summary["elapsed_seconds"] = elapsed
        summary["config"] = asdict(self.config)
        if self.custom_circuit_config:
            summary["custom_circuit_config"] = asdict(self.custom_circuit_config)
        
        self._print_summary(summary)
        return summary


class FailureProfileGenerator:
    """Generate parameter grids for failure profile tuning (Stage 1)."""
    
    @staticmethod
    def generate_parameter_grid() -> List[Dict[str, Any]]:
        """Generate grid of failure profile parameters to test."""
        
        # Base failure rates - vary these systematically
        api_timeout_rates = [0.15, 0.25, 0.35, 0.45]  # Higher than control
        confidence_decay_rates = [0.20, 0.30, 0.40, 0.50]
        context_overflow_rates = [0.10, 0.15, 0.25, 0.35] 
        cascading_rates = [0.05, 0.15, 0.25, 0.40]
        
        # Generate all combinations (will be large - consider sampling)
        combinations = []
        for api_rate, conf_rate, ctx_rate, casc_rate in itertools.product(
            api_timeout_rates, confidence_decay_rates, 
            context_overflow_rates, cascading_rates
        ):
            # Skip combinations that are too extreme (>80% total failure)
            total_failure_pressure = api_rate + conf_rate + ctx_rate + casc_rate
            if total_failure_pressure > 1.2:  # Allow some overlap
                continue
                
            combinations.append({
                "failure_rates": {
                    "api_timeout": api_rate,
                    "confidence_decay": conf_rate, 
                    "context_overflow": ctx_rate,
                    "cascading_hallucination": casc_rate
                },
                "workload": "stress",  # Use stress workload template
                "expected_success_rate": max(0.1, 1.0 - (total_failure_pressure * 0.4))
            })
            
        return combinations


class BreakerThresholdGenerator:
    """Generate parameter grids for circuit breaker tuning (Stage 2)."""
    
    @staticmethod  
    def generate_parameter_grid() -> List[Dict[str, Any]]:
        """Generate grid of circuit breaker parameters to test."""
        
        # Circuit breaker thresholds - focus on timing and sensitivity
        failure_thresholds = [2, 3, 4, 5]  # Trips after N failures
        timeout_seconds = [15.0, 30.0, 45.0, 60.0]  # Recovery window
        half_open_max_calls = [1, 3, 5]  # Test calls in half-open state
        confidence_thresholds = [0.3, 0.5, 0.7]  # Confidence trip point
        
        combinations = []
        for fail_thresh, timeout, half_open, conf_thresh in itertools.product(
            failure_thresholds, timeout_seconds, half_open_max_calls, confidence_thresholds
        ):
            combinations.append({
                "circuit_config": {
                    "failure_threshold": fail_thresh,
                    "timeout_seconds": timeout,
                    "half_open_max_calls": half_open,
                    "confidence_threshold": conf_thresh,
                    "context_threshold": 6000,  # Keep constant
                    "predictability_min": 0.3   # Keep constant
                },
                "condition": "AI_CB"  # Test with AI circuit breaker
            })
            
        return combinations


class TuningHarness:
    """Main harness for automated parameter tuning."""
    
    def __init__(self, results_dir: Path = None, runs_per_condition: int = 3):
        self.results_dir = results_dir or Path("results/tuning")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.results_dir / "tuning-log.jsonl"
        self.checkpoint_file = self.results_dir / "checkpoint.json"
        self.runs_per_condition = runs_per_condition
        
        # Load existing checkpoint if resuming
        self.completed_runs = self._load_checkpoint()
        
    def _load_checkpoint(self) -> set:
        """Load completed run IDs from checkpoint file."""
        if not self.checkpoint_file.exists():
            return set()
            
        try:
            with open(self.checkpoint_file) as f:
                checkpoint = json.load(f)
                return set(checkpoint.get("completed_runs", []))
        except Exception:
            return set()
    
    def _save_checkpoint(self, run_id: str):
        """Save progress checkpoint."""
        self.completed_runs.add(run_id)
        checkpoint = {
            "completed_runs": list(self.completed_runs),
            "last_updated": datetime.now().isoformat()
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    
    def _log_result(self, result: TuningResult):
        """Append result to JSONL log file."""
        # Convert ParameterSet (NamedTuple) to dict for JSON serialization
        result_dict = asdict(result)
        result_dict["parameter_set"] = {
            "stage": result.parameter_set.stage,
            "params": result.parameter_set.params,
            "run_id": result.parameter_set.run_id
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(result_dict) + '\n')
    
    def _generate_run_id(self, stage: str, param_idx: int) -> str:
        """Generate unique run ID for parameter set."""
        return f"{stage}_{param_idx:04d}_{int(time.time())}"
    
    def _create_simulator_config(self, param_set: ParameterSet) -> SimulatorConfig:
        """Create SimulatorConfig from parameter set."""
        base_config = {
            "runs": self.runs_per_condition,
            "turn_budget": 25,
            "verbose": False,
            "seed": hash(param_set.run_id) % 2**31,  # Deterministic per param set
        }
        
        if param_set.stage == "failure":
            # Stage 1: Test failure profiles with fixed breaker
            base_config.update({
                "workload": param_set.params.get("workload", "stress"),
                "condition": "SIMPLE_CB"  # Use simple breaker consistently
            })
            
        elif param_set.stage == "breaker": 
            # Stage 2: Test breaker configs with fixed failure profile
            base_config.update({
                "workload": "stress",  # Use stress or a known-good failure profile
                "condition": param_set.params.get("condition", "AI_CB")
            })
        
        return SimulatorConfig(**base_config)
    
    def _create_custom_workload(self, param_set: ParameterSet, config: SimulatorConfig) -> Optional[str]:
        """Create temporary workload file for custom failure rates."""
        if param_set.stage != "failure" or "failure_rates" not in param_set.params:
            return None
            
        # Create temporary workload based on stress template
        temp_workload_name = f"temp_{param_set.run_id}"
        temp_dir = Path("workloads") / temp_workload_name
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Load stress template and modify failure rates
        stress_config_path = Path("workloads/stress/config.json")
        with open(stress_config_path) as f:
            workload_config = json.load(f)
            
        # Update with custom failure rates
        workload_config["failure_rates"] = param_set.params["failure_rates"]
        workload_config["expected_success_rate"] = param_set.params.get(
            "expected_success_rate", 0.3
        )
        workload_config["name"] = f"temp_{param_set.run_id}"
        
        # Save temporary workload
        with open(temp_dir / "config.json", 'w') as f:
            json.dump(workload_config, f, indent=2)
            
        return temp_workload_name
    
    def _cleanup_temp_workload(self, workload_name: str):
        """Remove temporary workload directory."""
        if workload_name and workload_name.startswith("temp_"):
            temp_dir = Path("workloads") / workload_name
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
    
    def _evaluate_parameter_set(self, param_set: ParameterSet) -> TuningResult:
        """Evaluate a single parameter set by running simulator."""
        
        print(f"Evaluating {param_set.run_id} (Stage: {param_set.stage})")
        
        start_time = time.time()
        temp_workload = None
        
        try:
            # Create simulator configuration
            config = self._create_simulator_config(param_set)
            
            # Handle custom failure profiles (Stage 1)
            if param_set.stage == "failure":
                temp_workload = self._create_custom_workload(param_set, config)
                if temp_workload:
                    config.workload = temp_workload
            
            # Handle custom circuit breaker configs (Stage 2)  
            circuit_config = None
            if param_set.stage == "breaker" and "circuit_config" in param_set.params:
                circuit_config = CircuitConfig(**param_set.params["circuit_config"])
            
            # Run simulation using custom runner that supports circuit config injection
            runner = TuningSimulatorRunner(config, circuit_config)
            summary_result = runner.run_all()
            
            # Extract individual run results for analysis
            results = runner.results
            
            # Extract key metrics for tuning decisions
            metrics = self._extract_tuning_metrics(results, param_set)
            
            # Cleanup temporary files
            if temp_workload:
                self._cleanup_temp_workload(temp_workload)
            
            return TuningResult(
                parameter_set=param_set,
                timestamp=datetime.now().isoformat(),
                metrics=metrics,
                runs_completed=len(results),
                runs_attempted=config.runs,
                success=True
            )
            
        except Exception as e:
            # Cleanup on error
            if temp_workload:
                self._cleanup_temp_workload(temp_workload)
                
            return TuningResult(
                parameter_set=param_set,
                timestamp=datetime.now().isoformat(), 
                metrics={},
                runs_completed=0,
                runs_attempted=self.runs_per_condition,
                success=False,
                error_message=str(e)
            )
    
    def _extract_tuning_metrics(self, results: List[Dict], param_set: ParameterSet) -> Dict[str, Any]:
        """Extract key metrics for tuning decisions."""
        
        if not results:
            return {"error": "no_results"}
        
        # Extract metrics from simulator results
        
        # Aggregate metrics across all runs
        total_turns = []
        recovery_attempts = []
        completions = []
        total_tokens = []
        circuit_trips = []
        trip_turns = []
        
        for run_result in results:
            run_metrics = run_result.get("metrics", {})
            
            total_turns.append(run_metrics.get("total_turns", 0))
            completions.append(1 if run_metrics.get("task_completed", False) else 0)
            total_tokens.append(run_metrics.get("total_token_usage", 0))
            
            # Track circuit breaker activity - trips are directly in metrics
            trips = run_metrics.get("circuit_trips", 0)
            circuit_trips.append(trips)
            
            # Count recovery attempts - directly in metrics
            recovery_count = run_metrics.get("recovery_attempts", 0)
            recovery_attempts.append(recovery_count)
            
            # TODO: Extract trip turn information from circuit breaker objects
            # For now, we'll need to examine the circuit_breaker_a/b results
            # This might require additional parsing of the circuit breaker state
        
        # Calculate aggregate statistics
        metrics = {
            "avg_turns": sum(total_turns) / len(total_turns) if total_turns else 0,
            "completion_rate": sum(completions) / len(completions) if completions else 0,
            "avg_tokens": sum(total_tokens) / len(total_tokens) if total_tokens else 0,
            "avg_circuit_trips": sum(circuit_trips) / len(circuit_trips) if circuit_trips else 0,
            "recovery_attempt_rate": sum(recovery_attempts) / len(recovery_attempts) if recovery_attempts else 0,
            "runs_with_trips": len([t for t in circuit_trips if t > 0]),
            "runs_with_recovery": len([r for r in recovery_attempts if r > 0]),
        }
        
        # Target metrics for Stage 1 (failure profiles)
        if param_set.stage == "failure":
            metrics.update({
                "avg_trip_turn": sum(trip_turns) / len(trip_turns) if trip_turns else None,
                "trips_in_target_range": len([t for t in trip_turns if 6 <= t <= 10]),
                "failure_rate_pressure": sum(param_set.params.get("failure_rates", {}).values()),
            })
            
        # Target metrics for Stage 2 (breaker tuning)
        elif param_set.stage == "breaker":
            circuit_params = param_set.params.get("circuit_config", {})
            metrics.update({
                "breaker_sensitivity": circuit_params.get("failure_threshold", 0),
                "recovery_window": circuit_params.get("timeout_seconds", 0),
                "half_open_samples": circuit_params.get("half_open_max_calls", 0),
            })
        
        return metrics
    
    def run_stage(self, stage: str, dry_run: bool = False, max_combinations: int = None) -> List[TuningResult]:
        """Run tuning for specified stage."""
        
        print(f"Starting Stage: {stage}")
        
        # Generate parameter grid
        if stage == "failure":
            param_grid = FailureProfileGenerator.generate_parameter_grid()
        elif stage == "breaker":
            param_grid = BreakerThresholdGenerator.generate_parameter_grid()
        else:
            raise ValueError(f"Unknown stage: {stage}")
        
        # Limit combinations if requested
        if max_combinations:
            param_grid = param_grid[:max_combinations]
        
        print(f"Generated {len(param_grid)} parameter combinations")
        
        if dry_run:
            print("DRY RUN - Parameter combinations:")
            for i, params in enumerate(param_grid[:5]):  # Show first 5
                print(f"  {i+1}: {params}")
            if len(param_grid) > 5:
                print(f"  ... and {len(param_grid) - 5} more")
            return []
        
        # Convert to parameter sets
        parameter_sets = []
        for i, params in enumerate(param_grid):
            run_id = self._generate_run_id(stage, i)
            if run_id not in self.completed_runs:
                parameter_sets.append(ParameterSet(stage, params, run_id))
        
        print(f"Running {len(parameter_sets)} parameter sets ({len(self.completed_runs)} already completed)")
        
        # Execute parameter sets
        results = []
        for i, param_set in enumerate(parameter_sets):
            print(f"Progress: {i+1}/{len(parameter_sets)}")
            
            result = self._evaluate_parameter_set(param_set)
            results.append(result)
            
            # Log and checkpoint
            self._log_result(result)
            self._save_checkpoint(param_set.run_id)
            
            if result.success:
                self._print_result_summary(result)
            else:
                print(f"  ERROR: {result.error_message}")
        
        return results
    
    def _print_result_summary(self, result: TuningResult):
        """Print concise summary of result."""
        metrics = result.metrics
        
        if result.parameter_set.stage == "failure":
            trip_turn = metrics.get("avg_trip_turn", "N/A")
            recovery_rate = metrics.get("recovery_attempt_rate", 0)
            print(f"  Trip turn: {trip_turn}, Recovery rate: {recovery_rate:.2f}, Completion: {metrics.get('completion_rate', 0):.2f}")
        
        elif result.parameter_set.stage == "breaker":
            trips = metrics.get("avg_circuit_trips", 0)
            recovery_rate = metrics.get("recovery_attempt_rate", 0)
            print(f"  Avg trips: {trips:.1f}, Recovery rate: {recovery_rate:.2f}, Completion: {metrics.get('completion_rate', 0):.2f}")
    
    def analyze_results(self, stage: str = None) -> Dict[str, Any]:
        """Analyze logged results and recommend best parameters."""
        
        if not self.log_file.exists():
            return {"error": "No results file found"}
        
        # Load all results
        results = []
        with open(self.log_file) as f:
            for line in f:
                try:
                    result_data = json.loads(line.strip())
                    if stage is None or result_data.get("parameter_set", {}).get("stage") == stage:
                        results.append(result_data)
                except json.JSONDecodeError:
                    continue
        
        if not results:
            return {"error": f"No results found for stage: {stage}"}
        
        # Analyze for optimal configurations
        analysis = {"total_results": len(results)}
        
        if stage == "failure" or (stage is None and any(r.get("parameter_set", {}).get("stage") == "failure" for r in results)):
            analysis["failure_analysis"] = self._analyze_failure_stage(
                [r for r in results if r.get("parameter_set", {}).get("stage") == "failure"]
            )
        
        if stage == "breaker" or (stage is None and any(r.get("parameter_set", {}).get("stage") == "breaker" for r in results)):
            analysis["breaker_analysis"] = self._analyze_breaker_stage(
                [r for r in results if r.get("parameter_set", {}).get("stage") == "breaker"]
            )
        
        return analysis
    
    def _analyze_failure_stage(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze Stage 1 (failure profile) results."""
        
        # Find configurations with trips in target range (turns 6-10)
        target_configs = []
        for result in results:
            if not result.get("success", False):
                continue
                
            metrics = result.get("metrics", {})
            trips_in_range = metrics.get("trips_in_target_range", 0)
            avg_trip_turn = metrics.get("avg_trip_turn")
            recovery_rate = metrics.get("recovery_attempt_rate", 0)
            
            if avg_trip_turn and 6 <= avg_trip_turn <= 10 and recovery_rate > 0:
                target_configs.append({
                    "parameter_set": result["parameter_set"],
                    "avg_trip_turn": avg_trip_turn,
                    "recovery_rate": recovery_rate,
                    "completion_rate": metrics.get("completion_rate", 0),
                    "score": recovery_rate * metrics.get("completion_rate", 0)  # Combined score
                })
        
        # Sort by score
        target_configs.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "total_evaluated": len(results),
            "configs_in_target_range": len(target_configs),
            "top_configs": target_configs[:5],  # Top 5 by score
            "recommended": target_configs[0] if target_configs else None
        }
    
    def _analyze_breaker_stage(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyze Stage 2 (breaker threshold) results."""
        
        # Find configurations with good recovery and completion
        good_configs = []
        for result in results:
            if not result.get("success", False):
                continue
                
            metrics = result.get("metrics", {})
            recovery_rate = metrics.get("recovery_attempt_rate", 0)
            completion_rate = metrics.get("completion_rate", 0)
            
            if recovery_rate > 0.5 and completion_rate > 0.4:  # Reasonable thresholds
                good_configs.append({
                    "parameter_set": result["parameter_set"],
                    "recovery_rate": recovery_rate,
                    "completion_rate": completion_rate,
                    "avg_trips": metrics.get("avg_circuit_trips", 0),
                    "score": recovery_rate * completion_rate  # Combined score
                })
        
        # Sort by score
        good_configs.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "total_evaluated": len(results),
            "good_configs": len(good_configs),
            "top_configs": good_configs[:5],  # Top 5 by score
            "recommended": good_configs[0] if good_configs else None
        }


def main():
    parser = argparse.ArgumentParser(description="Automated tuning harness for exp-001b simulator")
    
    parser.add_argument("--stage", choices=["failure", "breaker"], 
                       help="Tuning stage: 'failure' for failure profiles, 'breaker' for circuit breaker thresholds")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from last checkpoint")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show parameter grid without running simulations")
    parser.add_argument("--analyze", action="store_true",
                       help="Analyze existing results and show recommendations")
    parser.add_argument("--runs-per-condition", type=int, default=3,
                       help="Number of simulation runs per parameter set (default: 3)")
    parser.add_argument("--max-combinations", type=int,
                       help="Limit number of parameter combinations to test")
    parser.add_argument("--results-dir", type=Path, default=Path("results/tuning"),
                       help="Directory for results and logs")
    
    args = parser.parse_args()
    
    # Create harness
    harness = TuningHarness(
        results_dir=args.results_dir,
        runs_per_condition=args.runs_per_condition
    )
    
    if args.analyze:
        # Analyze existing results
        analysis = harness.analyze_results(args.stage)
        print(json.dumps(analysis, indent=2))
        return
    
    if not args.stage and not args.resume:
        parser.error("Must specify --stage or --resume")
    
    # Determine stage to run
    if args.resume:
        # For resume, we'd need to track which stage was being run
        # For now, require explicit stage
        if not args.stage:
            parser.error("Must specify --stage when using --resume")
    
    # Run tuning stage
    results = harness.run_stage(
        args.stage, 
        dry_run=args.dry_run,
        max_combinations=args.max_combinations
    )
    
    if not args.dry_run:
        print(f"\nCompleted {len(results)} parameter sets")
        successful = [r for r in results if r.success]
        print(f"Successful: {len(successful)}/{len(results)}")
        
        if successful:
            print(f"Results logged to: {harness.log_file}")
            print("Run with --analyze to see recommendations")


if __name__ == "__main__":
    main()