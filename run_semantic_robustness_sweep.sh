#!/usr/bin/env bash
set -euo pipefail

mkdir -p results

INPUT="benchmark_eval/data/gaia_subset.jsonl"
RATES=("0.1" "0.3" "0.5")
POLICIES=("no_cb" "ai_cb" "adaptive_cb")
REPEATS=5

run_one() {
  local policy="$1"
  local rate="$2"
  local run_idx="$3"
  local rate_tag="${rate/./}"

  local name="semantic_p${rate_tag}_${policy}_run${run_idx}"

  echo "=== Running ${name} ==="
  python -m benchmark_eval.src.run_eval \
    --input "${INPUT}" \
    --output "results/${name}.jsonl" \
    --policy "${policy}" \
    --execution-mode state_locked \
    --fault-type semantic \
    --inject-rate "${rate}"

  echo "=== Summarizing ${name} ==="
  python -m benchmark_eval.src.summarize_results \
    --input "results/${name}.jsonl" \
    --output-csv "results/${name}.csv" \
    --output-tex "results/${name}.tex"
}

aggregate_bucket() {
  local policy="$1"
  local rate="$2"
  local rate_tag="${rate/./}"
  local prefix="semantic_p${rate_tag}_${policy}"
  local agg="results/${prefix}_all.jsonl"

  echo "=== Aggregating ${prefix} ==="
  cat results/${prefix}_run*.jsonl > "${agg}"

  echo "=== Summarizing aggregate ${prefix} ==="
  python -m benchmark_eval.src.summarize_results \
    --input "${agg}" \
    --output-csv "results/${prefix}_all.csv" \
    --output-tex "results/${prefix}_all.tex"

  echo "=== Realized corruption rate: ${prefix} ==="
  jq -s '((map(select(.upstream_corrupted == true)) | length) / length)' "${agg}"

  echo "=== Conditional counts: ${prefix} ==="
  jq -s '{
    runs: length,
    corrupted: map(select(.upstream_corrupted == true)) | length,
    clean: map(select(.upstream_corrupted != true)) | length,
    cascades: map(select(.cascade == true)) | length,
    corrupted_and_cascade: map(select(.upstream_corrupted == true and .cascade == true)) | length,
    clean_and_cascade: map(select(.upstream_corrupted != true and .cascade == true)) | length
  }' "${agg}"

  echo "=== Trip selectivity via trip_count: ${prefix} ==="
  jq -s '
  {
    trip_corrupted: (map(select(.upstream_corrupted == true and .trip_count > 0)) | length),
    corrupted: (map(select(.upstream_corrupted == true)) | length),
    trip_clean: (map(select(.upstream_corrupted != true and .trip_count > 0)) | length),
    clean: (map(select(.upstream_corrupted != true)) | length)
  }
  | {
    p_trip_corrupted: (if .corrupted > 0 then (.trip_corrupted / .corrupted) else 0 end),
    p_trip_clean: (if .clean > 0 then (.trip_clean / .clean) else 0 end),
    selectivity_gap: (
      (if .corrupted > 0 then (.trip_corrupted / .corrupted) else 0 end) -
      (if .clean > 0 then (.trip_clean / .clean) else 0 end)
    )
  }' "${agg}"

  echo "=== CSV: ${prefix} ==="
  cat "results/${prefix}_all.csv"
  echo
}

compute_selectivity_stats() {
  local policy="$1"
  local rate="$2"
  local rate_tag="${rate/./}"
  local agg="results/semantic_p${rate_tag}_${policy}_all.jsonl"

  echo "=== Selectivity significance test: semantic_p${rate_tag}_${policy} ==="
  python - << EOF
import json
from pathlib import Path
from statsmodels.stats.proportion import proportions_ztest

path = Path("${agg}")
trip_corrupted = corrupted = trip_clean = clean = 0

with path.open("r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        corrupted_flag = bool(obj.get("upstream_corrupted", False))
        tripped_flag = float(obj.get("trip_count", 0)) > 0
        if corrupted_flag:
            corrupted += 1
            if tripped_flag:
                trip_corrupted += 1
        else:
            clean += 1
            if tripped_flag:
                trip_clean += 1

print({
    "trip_corrupted": trip_corrupted,
    "corrupted": corrupted,
    "trip_clean": trip_clean,
    "clean": clean,
})

if corrupted > 0 and clean > 0:
    count = [trip_corrupted, trip_clean]
    nobs = [corrupted, clean]
    stat, pval = proportions_ztest(count, nobs)
    p1 = trip_corrupted / corrupted
    p2 = trip_clean / clean
    diff = p1 - p2
    print({
        "p_trip_corrupted": round(p1, 6),
        "p_trip_clean": round(p2, 6),
        "selectivity_gap": round(diff, 6),
        "z": round(float(stat), 6),
        "p_value": round(float(pval), 6),
    })
else:
    print({"error": "invalid denominators"})
EOF
  echo
}

echo "===== Phase 1: Per-run evaluations ====="
for rate in "${RATES[@]}"; do
  for policy in "${POLICIES[@]}"; do
    for run_idx in $(seq 1 ${REPEATS}); do
      run_one "${policy}" "${rate}" "${run_idx}"
      sleep 2
    done
  done
done

echo "===== Phase 2: Aggregate by policy x rate ====="
for rate in "${RATES[@]}"; do
  for policy in "${POLICIES[@]}"; do
    aggregate_bucket "${policy}" "${rate}"
  done
done

echo "===== Phase 3: Selectivity significance tests ====="
for rate in "${RATES[@]}"; do
  for policy in "${POLICIES[@]}"; do
    compute_selectivity_stats "${policy}" "${rate}"
  done
done

echo "===== Phase 4: Final recap ====="
for rate in "${RATES[@]}"; do
  rate_tag="${rate/./}"
  for policy in "${POLICIES[@]}"; do
    echo "--- results/semantic_p${rate_tag}_${policy}_all.csv ---"
    cat "results/semantic_p${rate_tag}_${policy}_all.csv"
    echo
  done
done

echo "===== Done ====="
