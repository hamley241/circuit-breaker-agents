#!/usr/bin/env bash
set -euo pipefail

PYTHON=./benchmark_eval/.venv/bin/python
INPUT=benchmark_eval/data/gaia_subset.jsonl
OUTPUT_DIR=results
REPEATS=${REPEATS:-5}
MAX_PARALLEL=${MAX_PARALLEL:-15}
INJECT_RATE=0.7

run_one() {
    local variant=$1
    local run_id=$2
    local seed=$((100 + run_id))
    local output="${OUTPUT_DIR}/manip_cross_stage_${variant}_p07_run${run_id}.jsonl"
    local log="${OUTPUT_DIR}/manip_cross_stage_${variant}_p07_run${run_id}.log"
    echo "[START] ${variant} run${run_id} seed=${seed}"
    $PYTHON -m benchmark_eval.src.run_eval \
        --input "$INPUT" \
        --output "$output" \
        --policy no_cb \
        --mode observer \
        --verifier cross_stage \
        --verifier-variant "$variant" \
        --execution-mode state_locked \
        --pipeline-variant three_stage \
        --fault-type semantic \
        --inject-rate "$INJECT_RATE" \
        --compute-oracle \
        --seed "$seed" \
        > "$log" 2>&1 && echo "[DONE ] ${variant} run${run_id}" || echo "[FAIL ] ${variant} run${run_id} — see ${log}"
}

export -f run_one
export PYTHON INPUT OUTPUT_DIR INJECT_RATE

mkdir -p "$OUTPUT_DIR"

for variant in correct ablated wrong_spec; do
    for i in $(seq 1 "$REPEATS"); do
        echo "$variant $i"
    done
done | xargs -P "$MAX_PARALLEL" -n 2 bash -c 'run_one "$@"' _

echo "All runs complete"
