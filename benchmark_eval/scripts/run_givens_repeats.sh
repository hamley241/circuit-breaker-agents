#!/usr/bin/env bash
set -euo pipefail

PYTHON=./benchmark_eval/.venv/bin/python
INPUT=benchmark_eval/data/gaia_subset.jsonl
OUTPUT_DIR=results
REPEATS=${REPEATS:-5}
MAX_PARALLEL=${MAX_PARALLEL:-5}
INJECT_RATE=0.7
PREFIX=givens_corruption_p07

mkdir -p "$OUTPUT_DIR"

run_one() {
    local run_id=$1
    local seed=$((100 + run_id))
    local output="${OUTPUT_DIR}/${PREFIX}_run${run_id}.jsonl"
    local log="${OUTPUT_DIR}/${PREFIX}_run${run_id}.log"
    echo "[START] run${run_id} seed=${seed}"
    $PYTHON -m benchmark_eval.src.run_eval \
        --input "$INPUT" \
        --output "$output" \
        --policy no_cb \
        --execution-mode state_locked \
        --pipeline-variant three_stage \
        --fault-type semantic \
        --inject-rate "$INJECT_RATE" \
        --compute-oracle \
        --seed "$seed" \
        > "$log" 2>&1 && echo "[DONE ] run${run_id}" || echo "[FAIL ] run${run_id} — see ${log}"
}

export -f run_one
export PYTHON INPUT OUTPUT_DIR PREFIX INJECT_RATE

seq 1 "$REPEATS" | xargs -P "$MAX_PARALLEL" -I{} bash -c 'run_one "$@"' _ {}

echo "All ${REPEATS} runs complete"
