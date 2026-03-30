"""Modal entrypoint for exp-001 circuit breaker experiment (simulated and real API runs)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
REMOTE_EXP_DIR = "/app/exp-001"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install([
        "numpy>=1.24.0",
        "openai>=1.12.0", 
        "anthropic>=0.18.0"
    ])
    .add_local_dir(HERE, REMOTE_EXP_DIR)
)

app = modal.App("exp-001-modal-runner")


@app.function(
    image=image,
    timeout=60 * 60,  # 1 hour per invocation
    secrets=[
        modal.Secret.from_name("openai-api-key"),
        modal.Secret.from_name("anthropic-api-key")
    ]
)
def run_experiment(runs_per_condition: int = 10, pilot: bool = True, real_mode: bool = False):
    """Execute the experiment inside Modal with simulated or real API calls."""
    if REMOTE_EXP_DIR not in sys.path:
        sys.path.append(REMOTE_EXP_DIR)

    from experiment_runner import ExperimentRunner  # type: ignore

    runner = ExperimentRunner(
        runs_per_condition=runs_per_condition, 
        pilot=pilot,
        real_mode=real_mode
    )
    summary = runner.run_all()
    return {
        "summary": summary,
        "runs": runner.results,
        "pilot": pilot,
        "runs_per_condition": runs_per_condition,
        "real_mode": real_mode,
    }


@app.local_entrypoint()
def main(
    runs: int = 10,
    full: bool = False,
    real: bool = False,
    output: str = "exp-001-modal-results.json",
):
    """Local CLI for launching the Modal experiment runner."""
    runs_per_condition = 55 if full else runs
    pilot = not full

    mode_str = "REAL API" if real else "SIMULATED"
    print(
        f"Launching Modal job ({mode_str} mode, runs/condition={runs_per_condition}, pilot={pilot})..."
    )
    result = run_experiment.remote(
        runs_per_condition=runs_per_condition, 
        pilot=pilot,
        real_mode=real
    )

    output_path = HERE / output
    output_path.write_text(json.dumps(result, indent=2))
    print(f"Saved Modal results to {output_path}")
