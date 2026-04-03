#!/usr/bin/env bash
set -euo pipefail

mkdir -p results

POLICIES=("no_cb" "ai_cb" "adaptive_cb")

for policy in "${POLICIES[@]}"; do
  for i in {1..5}; do
    name="semantic_p05_${policy}_run${i}"

    echo "=== Running $name ==="
    python -m benchmark_eval.src.run_eval \
      --input benchmark_eval/data/gaia_subset.jsonl \
      --output "results/${name}.jsonl" \
      --policy "${policy}" \
      --execution-mode state_locked \
      --fault-type semantic \
      --inject-rate 0.5

    echo "=== Summarizing $name ==="
    python -m benchmark_eval.src.summarize_results \
      --input "results/${name}.jsonl" \
      --output-csv "results/${name}.csv" \
      --output-tex "results/${name}.tex"
  done
done

jq -s '.' results/semantic_p05_no_cb_run*.jsonl > results/no_cb_all.jsonl
jq -s '.' results/semantic_p05_ai_cb_run*.jsonl > results/ai_cb_all.jsonl
jq -s '.' results/semantic_p05_adaptive_cb_run*.jsonl > results/adaptive_cb_all.jsonl



python -m benchmark_eval.src.summarize_results \
  --input results/no_cb_all.jsonl \
  --output-csv results/no_cb_all.csv \
  --output-tex results/no_cb_all.tex

python -m benchmark_eval.src.summarize_results \
  --input results/ai_cb_all.jsonl \
  --output-csv results/ai_cb_all.csv \
  --output-tex results/ai_cb_all.tex

python -m benchmark_eval.src.summarize_results \
  --input results/adaptive_cb_all.jsonl \
  --output-csv results/adaptive_cb_all.csv \
  --output-tex results/adaptive_cb_all.tex


