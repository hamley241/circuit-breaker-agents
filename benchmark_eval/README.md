# benchmark_eval

Real-task benchmark harness for the `circuit-breaker-agents` repo.

This version is wired for the **OpenAI Python SDK** using the **Responses API**, which the official SDK describes as the primary API for model interaction. The official Python examples show `OpenAI().responses.create(...)` with `instructions` and `input`, and also note that Chat Completions remains supported. citeturn606981search1turn606981search2

## Default model

The scaffold defaults to:

- provider: `openai`
- model: `gpt-5.2`

That default is chosen because it appears in the current official Python SDK examples. You can override it with `MODEL_NAME`. citeturn606981search1

## What this includes

- `no_cb`, `ai_cb`, and `adaptive_cb` policies
- stage-level tracing for upstream failures, cascade failures, breaker trips, and fallback usage
- OpenAI-backed runner via `src/models.py`
- summary generation for success, CFR, safe-failure rate, and utility
- LaTeX table export for the paper

## Setup

```bash
cd benchmark_eval
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set OPENAI_API_KEY
bash scripts/run_sample.sh
```

You can also override the model directly:

```bash
MODEL_NAME=gpt-5.2 python -m src.run_eval \
  --input data/gaia_subset.jsonl \
  --policy all \
  --output results/raw_runs.jsonl
```

## Recommended repo layout

```text
circuit-breaker-agents/
  empirical_validation/
  outputs/
  paper/
  results/
  benchmark_eval/   # <- add this folder here
```

## Notes

- This is still a scaffold, not a finished GAIA integration.
- The bundled dataset is a small sample JSONL file so the harness is runnable immediately.
- `src/grader.py` is still simple exact match, so swap that once you move to a real benchmark subset.
- Keep this code isolated from the Monte Carlo scripts.
