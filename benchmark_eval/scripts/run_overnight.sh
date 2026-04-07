#!/usr/bin/env bash
set -euo pipefail

PYTHON=./benchmark_eval/.venv/bin/python
OUTPUT_DIR=results
REPEATS=${REPEATS:-5}
MAX_PARALLEL=${MAX_PARALLEL:-5}
INJECT_RATE=0.7

run_one() {
    local dataset=$1
    local verifier=$2
    local run_id=$3
    local seed=$((100 + run_id))
    local label=$(basename $dataset .jsonl)
    local output="${OUTPUT_DIR}/overnight_${label}_${verifier}_run${run_id}.jsonl"
    local log="${OUTPUT_DIR}/overnight_${label}_${verifier}_run${run_id}.log"
    echo "[START] ${label} ${verifier} run${run_id} seed=${seed}"
    $PYTHON -m benchmark_eval.src.run_eval \
        --input "$dataset" \
        --output "$output" \
        --policy no_cb \
        --mode observer \
        --verifier "$verifier" \
        --verifier-variant correct \
        --execution-mode state_locked \
        --pipeline-variant three_stage \
        --fault-type semantic \
        --inject-rate "$INJECT_RATE" \
        --compute-oracle \
        --seed "$seed" \
        > "$log" 2>&1 \
        && echo "[DONE ] ${label} ${verifier} run${run_id}" \
        || echo "[FAIL ] ${label} ${verifier} run${run_id} — see ${log}"
}

export -f run_one
export PYTHON OUTPUT_DIR INJECT_RATE
mkdir -p "$OUTPUT_DIR"

for dataset in benchmark_eval/data/gaia_subset.jsonl benchmark_eval/data/gsm8k_subset.jsonl; do
    for verifier in handoff_only handoff_plus_task; do
        for i in $(seq 1 "$REPEATS"); do
            echo "$dataset $verifier $i"
        done
    done
done | xargs -P "$MAX_PARALLEL" -n 3 bash -c 'run_one "$@"' _

echo "Overnight run complete"
