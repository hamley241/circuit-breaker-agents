#!/usr/bin/env bash
set -euo pipefail

RUNS=10000
PF=0.70
COST=5
MODE=linear_subtractive

for ALPHA in 0.3 0.5 0.7
do
  python simulate_circuit_breakers.py \
    --runs "${RUNS}" \
    --p-f "${PF}" \
    --fallback-degradation-mode "${MODE}" \
    --fallback-degradation-alpha "${ALPHA}" \
    --catastrophe-cost "${COST}" \
    --csv-out "results_linear_alpha_${ALPHA}.csv"
done
