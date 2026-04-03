#!/usr/bin/env bash
set -euo pipefail

mkdir -p results

POLICIES=("no_cb" "ai_cb" "adaptive_cb")

for policy in "${POLICIES[@]}"; do
  for i in {1..5}; do
    name="free_recovery_semantic_p05_${policy}_run${i}"

    echo "=== Running $name ==="
    python -m benchmark_eval.src.run_eval \
      --input benchmark_eval/data/gaia_subset.jsonl \
      --output "results/${name}.jsonl" \
      --policy "${policy}" \
      --execution-mode free_recovery \
      --fault-type semantic \
      --inject-rate 0.5

    echo "=== Summarizing $name ==="
    python -m benchmark_eval.src.summarize_results \
      --input "results/${name}.jsonl" \
      --output-csv "results/${name}.csv" \
      --output-tex "results/${name}.tex"
  done
done
