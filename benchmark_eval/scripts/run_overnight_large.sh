#!/usr/bin/env bash
set -euo pipefail

PYTHON=./benchmark_eval/.venv/bin/python
OUTPUT_DIR=results
REPEATS=${REPEATS:-3}
MAX_PARALLEL=${MAX_PARALLEL:-5}
INJECT_RATE=0.7
INPUT=benchmark_eval/data/gsm8k_full.jsonl

run_one() {
    local verifier=$1
    local run_id=$2
    local seed=$((200 + run_id))
    local output="${OUTPUT_DIR}/large_gsm8k_${verifier}_run${run_id}.jsonl"
    local log="${OUTPUT_DIR}/large_gsm8k_${verifier}_run${run_id}.log"
    echo "[START] ${verifier} run${run_id} seed=${seed}"
    $PYTHON -m benchmark_eval.src.run_eval \
        --input "$INPUT" \
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
        && echo "[DONE ] ${verifier} run${run_id}" \
        || echo "[FAIL ] ${verifier} run${run_id} — see ${log}"
}

export -f run_one
export PYTHON OUTPUT_DIR INJECT_RATE INPUT
mkdir -p "$OUTPUT_DIR"

for verifier in handoff_only handoff_plus_task; do
    for i in $(seq 1 "$REPEATS"); do
        echo "$verifier $i"
    done
done | xargs -P "$MAX_PARALLEL" -n 2 bash -c 'run_one "$@"' _

echo "All runs complete"
