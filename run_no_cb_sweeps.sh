#!/usr/bin/env bash
set -euo pipefail

mkdir -p results

INPUT="benchmark_eval/data/gaia_subset.jsonl"

run_eval() {
  local name="$1"
  local policy="$2"
  local execution_mode="$3"
  local fault_type="$4"
  local inject_rate="$5"

  echo "=== Running ${name} ==="
  python -m benchmark_eval.src.run_eval \
    --input "${INPUT}" \
    --output "results/${name}.jsonl" \
    --policy "${policy}" \
    --execution-mode "${execution_mode}" \
    --fault-type "${fault_type}" \
    --inject-rate "${inject_rate}"

  echo "=== Summarizing ${name} ==="
  python -m benchmark_eval.src.summarize_results \
    --input "results/${name}.jsonl" \
    --output-csv "results/${name}.csv" \
    --output-tex "results/${name}.tex"

  echo "=== Injection stats for ${name} ==="
  jq -s '((map(select(.upstream_corrupted == true)) | length) / length)' "results/${name}.jsonl"

  echo "=== Conditional counts for ${name} ==="
  jq -s '{
    runs: length,
    corrupted: map(select(.upstream_corrupted == true)) | length,
    cascades: map(select(.cascade == true)) | length,
    corrupted_and_cascade: map(select(.upstream_corrupted == true and .cascade == true)) | length
  }' "results/${name}.jsonl"

  echo "=== Cascade count for ${name} ==="
  grep '"cascade": true' "results/${name}.jsonl" | wc -l || true

  echo "=== CSV for ${name} ==="
  cat "results/${name}.csv"
  echo
}

echo "===== Phase 1: no_cb baseline and sweeps ====="

run_eval "state_locked_no_cb_baseline_v1"   "no_cb"       "state_locked" "none"       "0.0"
sleep 5
run_eval "state_locked_no_cb_semantic_v2"   "no_cb"       "state_locked" "semantic"   "0.2"
sleep 5
run_eval "state_locked_no_cb_semantic_v3"   "no_cb"       "state_locked" "semantic"   "0.5"
sleep 5
run_eval "state_locked_no_cb_structural_v2" "no_cb"       "state_locked" "structural" "0.2"
sleep 5
run_eval "state_locked_no_cb_structural_v3" "no_cb"       "state_locked" "structural" "0.5"

echo "===== Phase 2: CB comparison on most informative regime (semantic 0.5) ====="

sleep 10
run_eval "state_locked_ai_cb_semantic_v3"       "ai_cb"       "state_locked" "semantic" "0.5"
sleep 5
run_eval "state_locked_adaptive_cb_semantic_v3" "adaptive_cb" "state_locked" "semantic" "0.5"

echo "===== Final recap ====="
for f in \
  results/state_locked_no_cb_baseline_v1.csv \
  results/state_locked_no_cb_semantic_v2.csv \
  results/state_locked_no_cb_semantic_v3.csv \
  results/state_locked_no_cb_structural_v2.csv \
  results/state_locked_no_cb_structural_v3.csv \
  results/state_locked_ai_cb_semantic_v3.csv \
  results/state_locked_adaptive_cb_semantic_v3.csv
do
  echo "--- ${f} ---"
  cat "${f}"
  echo
done
