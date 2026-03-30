# Tuning Harness for exp-001b Circuit Breaker Experiments

This automated tuning harness systematically searches for optimal failure profiles and circuit breaker configurations to achieve the desired behavior: breakers tripping mid-run (turns 6-10) with successful recovery attempts.

## Quick Start

```bash
# Stage 1: Find failure profiles that cause mid-run trips
python3 tuning_harness.py --stage failure --max-combinations 10

# Stage 2: Optimize circuit breaker thresholds for best recovery
python3 tuning_harness.py --stage breaker --max-combinations 20

# Preview parameter combinations without running
python3 tuning_harness.py --stage failure --dry-run

# Resume interrupted search
python3 tuning_harness.py --stage failure --resume

# Analyze results and get recommendations
python3 tuning_harness.py --analyze --stage failure
```

## Two-Stage Search Strategy

### Stage 1: Failure Profile Tuning (`--stage failure`)
- **Goal:** Find failure rate combinations that cause circuit breakers to trip around turns 6-10
- **Parameters varied:** 
  - `api_timeout`: 0.15 to 0.45
  - `confidence_decay`: 0.20 to 0.50  
  - `context_overflow`: 0.10 to 0.35
  - `cascading_hallucination`: 0.05 to 0.40
- **Fixed:** Uses SIMPLE_CB circuit breaker for consistency
- **Key metrics:** Average trip turn, recovery attempt rate, completion rate

### Stage 2: Circuit Breaker Tuning (`--stage breaker`)  
- **Goal:** Optimize breaker sensitivity and recovery parameters
- **Parameters varied:**
  - `failure_threshold`: 2 to 5 failures before trip
  - `timeout_seconds`: 15 to 60 second recovery windows
  - `half_open_max_calls`: 1 to 5 test calls in half-open state
  - `confidence_threshold`: 0.3 to 0.7 confidence trip points
- **Fixed:** Uses stress workload or best profile from Stage 1
- **Key metrics:** Recovery success rate, completion rate, trip frequency

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--stage {failure,breaker}` | Which tuning stage to run | Required |
| `--resume` | Resume from checkpoint | Off |
| `--dry-run` | Show parameter grid without running | Off |
| `--analyze` | Analyze results and show top configs | Off |
| `--runs-per-condition` | Simulation runs per parameter set | 3 |
| `--max-combinations` | Limit parameter combinations tested | All |
| `--results-dir` | Directory for logs and checkpoints | `results/tuning` |

## Output Files

- **`results/tuning/tuning-log.jsonl`** - Append-only log of all results
- **`results/tuning/checkpoint.json`** - Resume state (completed run IDs)  
- **`workloads/temp_*`** - Temporary workload configs (auto-cleaned)

## Key Metrics Tracked

### Stage 1 (Failure Profiles)
- `avg_trip_turn` - When first circuit breaker trip occurs (target: 6-10)
- `recovery_attempt_rate` - Fraction of runs with recovery attempts  
- `completion_rate` - Fraction of runs that complete successfully
- `trips_in_target_range` - Number of runs with trips in turns 6-10

### Stage 2 (Circuit Breaker)  
- `recovery_attempt_rate` - How often recovery is attempted
- `completion_rate` - How often runs complete despite failures
- `avg_circuit_trips` - Average trips per run
- `breaker_sensitivity` - Configured failure threshold

## Analysis and Recommendations

```bash
# Get top-performing configurations
python3 tuning_harness.py --analyze --stage failure

# View all results for manual analysis
cat results/tuning/tuning-log.jsonl | jq .
```

The analyzer ranks configurations by a combined score of recovery rate × completion rate, identifying setups where:
1. Breakers trip in the target turn range (6-10)
2. Recovery mechanisms activate successfully  
3. Tasks still complete despite failures

## Workflow Example

1. **Start with failure profiles:**
   ```bash
   python3 tuning_harness.py --stage failure --max-combinations 50
   python3 tuning_harness.py --analyze --stage failure
   ```

2. **Use best profile for breaker tuning:**
   ```bash
   # Edit the failure rates in BreakerThresholdGenerator based on Stage 1 results
   python3 tuning_harness.py --stage breaker --max-combinations 100
   python3 tuning_harness.py --analyze --stage breaker
   ```

3. **Manual validation:**
   ```bash
   # Test recommended config with the main simulator
   python3 simulator.py --workload stress --condition AI_CB --runs 10 --verbose
   ```

## Implementation Notes

- **Deterministic:** Uses seeded randomness for reproducible results
- **Resumable:** Checkpoint system allows interrupting and restarting 
- **Modular:** Easy to extend with Bayesian optimization or other search strategies
- **Safe:** Creates temporary workloads, stays within experiment directory
- **Efficient:** Small batches (3 runs/condition) for rapid iteration

The harness is designed for iterative exploration—run small batches, analyze results, refine parameter ranges, and repeat until you find configurations that reliably produce the target behavior.