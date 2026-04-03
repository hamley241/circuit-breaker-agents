#!/usr/bin/env bash
set -euo pipefail

main() {
  local input="benchmark_eval/data/gaia_subset.jsonl"
  local repeats=3

  mkdir -p results

  echo "[INFO] Starting post-fix rerun"
  echo "[INFO] Input: ${input}"
  echo "[INFO] Repeats per policy: ${repeats}"
  echo "[INFO] Policies: no_cb, ai_cb, adaptive_cb"
  echo "[INFO] Parallelism: 3"

  run_all_evals "${input}" "${repeats}"
  summarize_all_runs "${repeats}"
  aggregate_all "${repeats}"
  summarize_aggregates

  echo "[DONE] All runs, summaries, and aggregates completed"
}

run_one() {
  local input="$1"
  local policy="$2"
  local run_id="$3"
  local name="rerun_p03_${policy}_run${run_id}"
  local output_jsonl="results/${name}.jsonl"
  local log_file="results/${name}.log"

  echo "[START] ${name} $(date '+%Y-%m-%d %H:%M:%S')"

  if python -m benchmark_eval.src.run_eval \
    --input "${input}" \
    --output "${output_jsonl}" \
    --policy "${policy}" \
    --execution-mode state_locked \
    --pipeline-variant three_stage \
    --fault-type semantic \
    --inject-rate 0.3 \
    > "${log_file}" 2>&1
  then
    echo "[DONE ] ${name} $(date '+%Y-%m-%d %H:%M:%S')"
  else
    echo "[FAIL ] ${name} (see ${log_file})" >&2
    return 1
  fi
}

run_all_evals() {
  local input="$1"
  local repeats="$2"
  local total=$((3 * repeats))
  local progress_file="results/.rerun_progress"
  local jobs_file="results/.rerun_jobs"

  : > "${progress_file}"
  : > "${jobs_file}"

  {
    local i
    for i in $(seq 1 "${repeats}"); do
      printf "no_cb %s\n" "${i}"
    done
    for i in $(seq 1 "${repeats}"); do
      printf "ai_cb %s\n" "${i}"
    done
    for i in $(seq 1 "${repeats}"); do
      printf "adaptive_cb %s\n" "${i}"
    done
  } > "${jobs_file}"

  export -f run_one
  export input

  echo "[INFO] Launching ${total} eval jobs"

  xargs -n 2 -P 3 bash -c '
    set -euo pipefail
    run_one "$input" "$1" "$2"
    echo 1 >> results/.rerun_progress
  ' _ < "${jobs_file}"

  local completed
  completed=$(wc -l < "${progress_file}" | tr -d ' ')
  echo "[INFO] Eval phase complete: ${completed}/${total} jobs finished"

  if [[ "${completed}" -ne "${total}" ]]; then
    echo "[ERROR] Expected ${total} completed jobs, found ${completed}" >&2
    return 1
  fi
}

summarize_one_run() {
  local policy="$1"
  local run_id="$2"
  local name="rerun_p03_${policy}_run${run_id}"
  local input_jsonl="results/${name}.jsonl"
  local output_csv="results/${name}.csv"
  local output_tex="results/${name}.tex"

  if [[ ! -f "${input_jsonl}" ]]; then
    echo "[WARN ] Missing run output, skipping summary: ${input_jsonl}" >&2
    return 1
  fi

  if [[ ! -s "${input_jsonl}" ]]; then
    echo "[WARN ] Empty run output, skipping summary: ${input_jsonl}" >&2
    return 1
  fi

  echo "[SUM  ] ${name}"

  python -m benchmark_eval.src.summarize_results \
    --input "${input_jsonl}" \
    --output-csv "${output_csv}" \
    --output-tex "${output_tex}"
}

summarize_all_runs() {
  local repeats="$1"
  local -a policies=("no_cb" "ai_cb" "adaptive_cb")
  local policy
  local i

  echo "[INFO] Summarizing per-run outputs"

  for policy in "${policies[@]}"; do
    for i in $(seq 1 "${repeats}"); do
      summarize_one_run "${policy}" "${i}"
    done
  done
}

aggregate_policy() {
  local policy="$1"
  local repeats="$2"
  local aggregate_jsonl="results/rerun_p03_${policy}_all.jsonl"
  local found=0
  local i
  local run_file

  echo "[AGG  ] ${policy}"

  : > "${aggregate_jsonl}"

  for i in $(seq 1 "${repeats}"); do
    run_file="results/rerun_p03_${policy}_run${i}.jsonl"
    if [[ -f "${run_file}" && -s "${run_file}" ]]; then
      cat "${run_file}" >> "${aggregate_jsonl}"
      found=1
    else
      echo "[WARN ] Skipping missing/empty file during aggregation: ${run_file}" >&2
    fi
  done

  if [[ "${found}" -eq 0 ]]; then
    echo "[ERROR] No valid run files found for policy ${policy}" >&2
    return 1
  fi
}

aggregate_combined() {
  local combined_jsonl="results/rerun_p03_combined_all.jsonl"
  local -a policies=("no_cb" "ai_cb" "adaptive_cb")
  local policy
  local policy_file
  local found=0

  echo "[AGG  ] combined"

  : > "${combined_jsonl}"

  for policy in "${policies[@]}"; do
    policy_file="results/rerun_p03_${policy}_all.jsonl"
    if [[ -f "${policy_file}" && -s "${policy_file}" ]]; then
      cat "${policy_file}" >> "${combined_jsonl}"
      found=1
    else
      echo "[WARN ] Skipping missing/empty aggregate file: ${policy_file}" >&2
    fi
  done

  if [[ "${found}" -eq 0 ]]; then
    echo "[ERROR] No valid policy aggregates found for combined aggregation" >&2
    return 1
  fi
}

aggregate_all() {
  local repeats="$1"
  local -a policies=("no_cb" "ai_cb" "adaptive_cb")
  local policy

  echo "[INFO] Aggregating run outputs"

  for policy in "${policies[@]}"; do
    aggregate_policy "${policy}" "${repeats}"
  done

  aggregate_combined
}

summarize_aggregate_file() {
  local input_jsonl="$1"
  local output_csv="$2"
  local output_tex="$3"
  local label="$4"

  if [[ ! -f "${input_jsonl}" ]]; then
    echo "[WARN ] Missing aggregate file, skipping summary: ${input_jsonl}" >&2
    return 1
  fi

  if [[ ! -s "${input_jsonl}" ]]; then
    echo "[WARN ] Empty aggregate file, skipping summary: ${input_jsonl}" >&2
    return 1
  fi

  echo "[SUMAG] ${label}"

  python -m benchmark_eval.src.summarize_results \
    --input "${input_jsonl}" \
    --output-csv "${output_csv}" \
    --output-tex "${output_tex}"
}

summarize_aggregates() {
  echo "[INFO] Summarizing aggregate outputs"

  summarize_aggregate_file \
    "results/rerun_p03_no_cb_all.jsonl" \
    "results/rerun_p03_no_cb_all.csv" \
    "results/rerun_p03_no_cb_all.tex" \
    "no_cb"

  summarize_aggregate_file \
    "results/rerun_p03_ai_cb_all.jsonl" \
    "results/rerun_p03_ai_cb_all.csv" \
    "results/rerun_p03_ai_cb_all.tex" \
    "ai_cb"

  summarize_aggregate_file \
    "results/rerun_p03_adaptive_cb_all.jsonl" \
    "results/rerun_p03_adaptive_cb_all.csv" \
    "results/rerun_p03_adaptive_cb_all.tex" \
    "adaptive_cb"

  summarize_aggregate_file \
    "results/rerun_p03_combined_all.jsonl" \
    "results/rerun_p03_combined_all.csv" \
    "results/rerun_p03_combined_all.tex" \
    "combined"
}

main "$@"
