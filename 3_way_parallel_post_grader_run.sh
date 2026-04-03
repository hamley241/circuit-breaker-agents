mkdir -p results

INPUT="benchmark_eval/data/gaia_subset.jsonl"

run_one() {
  policy="$1"
  i="$2"
  name="rerun_p03_${policy}_run${i}"

  python -m benchmark_eval.src.run_eval \
    --input "${INPUT}" \
    --output "results/${name}.jsonl" \
    --policy "${policy}" \
    --execution-mode state_locked \
    --pipeline-variant three_stage \
    --fault-type semantic \
    --inject-rate 0.3 \
    > "results/${name}.log" 2>&1
}

export -f run_one
export INPUT

printf "%s\n" \
  "no_cb 1" "no_cb 2" "no_cb 3" \
  "ai_cb 1" "ai_cb 2" "ai_cb 3" \
  "adaptive_cb 1" "adaptive_cb 2" "adaptive_cb 3" \
| xargs -n 2 -P 3 bash -c 'run_one "$@"' _

for policy in no_cb ai_cb adaptive_cb; do
  for i in 1 2 3; do
    name="rerun_p03_${policy}_run${i}"
    python -m benchmark_eval.src.summarize_results \
      --input "results/${name}.jsonl" \
      --output-csv "results/${name}.csv" \
      --output-tex "results/${name}.tex"
  done
done
