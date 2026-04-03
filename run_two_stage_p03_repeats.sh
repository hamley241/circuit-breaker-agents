#!/usr/bin/env bash
set -euo pipefail

mkdir -p results

INPUT="benchmark_eval/data/gaia_subset.jsonl"
POLICIES=("no_cb" "ai_cb" "adaptive_cb")
REPEATS=3

run_one() {
  local policy="$1"
  local run_idx="$2"
  local name="two_stage_semantic_p03_${policy}_run${run_idx}"

  echo "=== Running ${name} ==="
  python -m benchmark_eval.src.run_eval \
    --input "${INPUT}" \
    --output "results/${name}.jsonl" \
    --policy "${policy}" \
    --execution-mode state_locked \
    --pipeline-variant two_stage \
    --fault-type semantic \
    --inject-rate 0.3

  echo "=== Summarizing ${name} ==="
  python -m benchmark_eval.src.summarize_results \
    --input "results/${name}.jsonl" \
    --output-csv "results/${name}.csv" \
    --output-tex "results/${name}.tex"
}

aggregate_policy() {
  local policy="$1"
  local prefix="two_stage_semantic_p03_${policy}"
  local agg="results/${prefix}_all.jsonl"

  echo "=== Aggregating ${prefix} ==="
  cat results/${prefix}_run*.jsonl > "${agg}"

  echo "=== Summarizing aggregate ${prefix} ==="
  python -m benchmark_eval.src.summarize_results \
    --input "${agg}" \
    --output-csv "results/${prefix}_all.csv" \
    --output-tex "results/${prefix}_all.tex"

  echo "=== CSV for ${prefix} ==="
  cat "results/${prefix}_all.csv"
  echo
}

echo "===== Phase 1: Per-run evaluations ====="
for policy in "${POLICIES[@]}"; do
  for run_idx in $(seq 1 ${REPEATS}); do
    run_one "${policy}" "${run_idx}"
    sleep 2
  done
done

echo "===== Phase 2: Aggregate per policy ====="
for policy in "${POLICIES[@]}"; do
  aggregate_policy "${policy}"
done

echo "===== Phase 3: Combined summary ====="
cat \
  results/two_stage_semantic_p03_no_cb_all.jsonl \
  results/two_stage_semantic_p03_ai_cb_all.jsonl \
  results/two_stage_semantic_p03_adaptive_cb_all.jsonl \
  > results/two_stage_semantic_p03_combined_all.jsonl

python -m benchmark_eval.src.summarize_results \
  --input results/two_stage_semantic_p03_combined_all.jsonl \
  --output-csv results/two_stage_semantic_p03_combined_all.csv \
  --output-tex results/two_stage_semantic_p03_combined_all.tex

echo "=== Final combined CSV ==="
cat results/two_stage_semantic_p03_combined_all.csv
