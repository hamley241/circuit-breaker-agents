#!/usr/bin/env bash
set -euo pipefail

python -m src.run_eval \
  --input data/gaia_subset.jsonl \
  --policy all \
  --output results/raw_runs.jsonl

python -m src.summarize_results \
  --input results/raw_runs.jsonl \
  --output-csv results/summary.csv \
  --output-tex results/benchmark_table.tex \
  --catastrophe-cost 5
