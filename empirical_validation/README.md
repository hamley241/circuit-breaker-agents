# Empirical Validation Starter

This package is a clean, modular starter for adding a lightweight real-API validation section to the `circuit-breaker-agents` paper.

## What it does

- Runs a 3-agent chain: planner -> executor -> verifier
- Supports breaker variants: `no_cb`, `ai_cb`, `adaptive_cb`
- Applies controlled perturbations after the planner or executor
- Logs every run to JSONL
- Produces a CSV summary with core reliability metrics

## Suggested usage

Prototype locally first, then scale up run counts once prompts and metrics look stable.

## Setup

```bash
cd empirical_validation_starter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Populate `.env`:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
```

## Quick smoke test

```bash
python main.py --provider mock --runs 5 --cb-type no_cb --injection none
```

## Real API run

```bash
python main.py \
  --provider openai \
  --runs 30 \
  --cb-type ai_cb \
  --injection contradictory_fact \
  --inject-rate 0.2 \
  --dataset tasks/sample_tasks.jsonl
```

## Recommended first matrix

- `cb_type`: `no_cb`, `ai_cb`, `adaptive_cb`
- `injection`: `none`, `corrupt_json`, `contradictory_fact`, `context_overload`, `empty_tool_result`
- `inject_rate`: `0.0`, `0.2`

## Output files

- `outputs/raw_runs_<timestamp>.jsonl`
- `outputs/summary_<timestamp>.csv`

## Key definitions

A run is marked as a cascade when:
1. an upstream failure occurs,
2. a downstream agent consumes the bad artifact without containing it, and
3. the final answer fails evaluation.

## Notebook

Open `notebooks/analyze_results.ipynb` after generating outputs.
