#!/usr/bin/env bash
set -euo pipefail

RUNS=10000
PF=0.70
COST=5
ALPHA=0.5

for MODE in linear_subtractive linear_multiplicative exp
do
  python simulate_circuit_breakers.py \
    --runs "${RUNS}" \
    --p-f "${PF}" \
    --fallback-degradation-mode "${MODE}" \
    --fallback-degradation-alpha "${ALPHA}" \
    --catastrophe-cost "${COST}" \
    --csv-out "results_mode_${MODE}.csv"
done
