#!/usr/bin/env bash
set -euo pipefail

main() {
  local prefix="${1:-}"
  local inject_rate="${2:-}"
  local input="${3:-benchmark_eval/data/gaia_subset.jsonl}"
  local repeats="${REPEATS:-3}"
  local max_parallel="${MAX_PARALLEL:-3}"
  local execution_mode="${EXECUTION_MODE:-state_locked}"
  local pipeline_variant="${PIPELINE_VARIANT:-three_stage}"
  local fault_type="${FAULT_TYPE:-semantic}"
  local -a policies=("no_cb" "ai_cb" "adaptive_cb" "completeness_cb")

  if [[ -z "${prefix}" || -z "${inject_rate}" ]]; then
    echo "Usage: $0 <output-prefix> <inject-rate> [input-jsonl]" >&2
    echo "Example: $0 phaseB_p05 0.5" >&2
    return 1
  fi

  mkdir -p results

  echo "[INFO] Prefix: ${prefix}"
  echo "[INFO] Inject rate: ${inject_rate}"
  echo "[INFO] Input: ${input}"
  echo "[INFO] Repeats per policy: ${repeats}"
  echo "[INFO] Parallelism: ${max_parallel}"
  echo "[INFO] Policies: ${policies[*]}"
  echo "[INFO] execution_mode=${execution_mode} pipeline_variant=${pipeline_variant} fault_type=${fault_type}"

  ensure_prefix_is_safe "${prefix}" "${repeats}" "${policies[@]}"
  run_all_evals "${prefix}" "${inject_rate}" "${input}" "${repeats}" "${max_parallel}" "${execution_mode}" "${pipeline_variant}" "${fault_type}" "${policies[@]}"
  summarize_all_runs "${prefix}" "${repeats}" "${policies[@]}"
  aggregate_all "${prefix}" "${repeats}" "${policies[@]}"
  summarize_aggregates "${prefix}" "${policies[@]}"

  echo "[DONE] Completed run for prefix=${prefix}, inject_rate=${inject_rate}"
}

ensure_prefix_is_safe() {
  local prefix="$1"
  local repeats="$2"
  shift 2
  local -a policies=("$@")
  local policy
  local run_id
  local path
  local ext

  for policy in "${policies[@]}"; do
    for run_id in $(seq 1 "${repeats}"); do
      for ext in jsonl log csv tex; do
        path="results/${prefix}_${policy}_run${run_id}.${ext}"
        if [[ -e "${path}" ]]; then
          echo "[ERROR] Refusing to overwrite existing file: ${path}" >&2
          return 1
        fi
      done
    done
    for ext in jsonl csv tex; do
      path="results/${prefix}_${policy}_all.${ext}"
      if [[ -e "${path}" ]]; then
        echo "[ERROR] Refusing to overwrite existing aggregate: ${path}" >&2
        return 1
      fi
    done
  done

  for ext in jsonl csv tex; do
    path="results/${prefix}_combined_all.${ext}"
    if [[ -e "${path}" ]]; then
      echo "[ERROR] Refusing to overwrite existing combined aggregate: ${path}" >&2
      return 1
    fi
  done
}

run_one() {
  local input="$1"
  local prefix="$2"
  local policy="$3"
  local run_id="$4"
  local inject_rate="$5"
  local execution_mode="$6"
  local pipeline_variant="$7"
  local fault_type="$8"
  local name="${prefix}_${policy}_run${run_id}"
  local output_jsonl="results/${name}.jsonl"
  local log_file="results/${name}.log"

  echo "[START] ${name} $(date '+%Y-%m-%d %H:%M:%S')"

  if python -m benchmark_eval.src.run_eval \
    --input "${input}" \
    --output "${output_jsonl}" \
    --policy "${policy}" \
    --execution-mode "${execution_mode}" \
    --pipeline-variant "${pipeline_variant}" \
    --fault-type "${fault_type}" \
    --inject-rate "${inject_rate}" \
    > "${log_file}" 2>&1
  then
    echo "[DONE ] ${name} $(date '+%Y-%m-%d %H:%M:%S')"
  else
    echo "[FAIL ] ${name} (see ${log_file})" >&2
    return 1
  fi
}

run_all_evals() {
  local prefix="$1"
  local inject_rate="$2"
  local input="$3"
  local repeats="$4"
  local max_parallel="$5"
  local execution_mode="$6"
  local pipeline_variant="$7"
  local fault_type="$8"
  shift 8
  local -a policies=("$@")
  local progress_file="results/.${prefix}_progress"
  local jobs_file="results/.${prefix}_jobs"
  local total=0
  local policy
  local i
  local completed

  : > "${progress_file}"
  : > "${jobs_file}"

  for policy in "${policies[@]}"; do
    for i in $(seq 1 "${repeats}"); do
      printf "%s %s\n" "${policy}" "${i}" >> "${jobs_file}"
      total=$((total + 1))
    done
  done

  export -f run_one
  export input prefix inject_rate execution_mode pipeline_variant fault_type

  echo "[INFO] Launching ${total} eval jobs"

  xargs -n 2 -P "${max_parallel}" bash -c '
    set -euo pipefail
    run_one "$input" "$prefix" "$1" "$2" "$inject_rate" "$execution_mode" "$pipeline_variant" "$fault_type"
    echo 1 >> "results/.${prefix}_progress"
  ' _ < "${jobs_file}"

  completed=$(wc -l < "${progress_file}" | tr -d ' ')
  echo "[INFO] Eval phase complete: ${completed}/${total} jobs finished"

  if [[ "${completed}" -ne "${total}" ]]; then
    echo "[ERROR] Expected ${total} completed jobs, found ${completed}" >&2
    return 1
  fi
}

summarize_one_run() {
  local prefix="$1"
  local policy="$2"
  local run_id="$3"
  local name="${prefix}_${policy}_run${run_id}"
  local input_jsonl="results/${name}.jsonl"
  local output_csv="results/${name}.csv"
  local output_tex="results/${name}.tex"

  if [[ ! -f "${input_jsonl}" ]]; then
    echo "[ERROR] Missing run output: ${input_jsonl}" >&2
    return 1
  fi
  if [[ ! -s "${input_jsonl}" ]]; then
    echo "[ERROR] Empty run output: ${input_jsonl}" >&2
    return 1
  fi

  echo "[SUM  ] ${name}"

  python -m benchmark_eval.src.summarize_results \
    --input "${input_jsonl}" \
    --output-csv "${output_csv}" \
    --output-tex "${output_tex}"
}

summarize_all_runs() {
  local prefix="$1"
  local repeats="$2"
  shift 2
  local -a policies=("$@")
  local policy
  local i

  echo "[INFO] Summarizing per-run outputs"

  for policy in "${policies[@]}"; do
    for i in $(seq 1 "${repeats}"); do
      summarize_one_run "${prefix}" "${policy}" "${i}"
    done
  done
}

aggregate_policy() {
  local prefix="$1"
  local policy="$2"
  local repeats="$3"
  local aggregate_jsonl="results/${prefix}_${policy}_all.jsonl"
  local i
  local run_file

  echo "[AGG  ] ${prefix}_${policy}"

  : > "${aggregate_jsonl}"

  for i in $(seq 1 "${repeats}"); do
    run_file="results/${prefix}_${policy}_run${i}.jsonl"
    if [[ ! -f "${run_file}" || ! -s "${run_file}" ]]; then
      echo "[ERROR] Missing/empty run file during aggregation: ${run_file}" >&2
      return 1
    fi
    cat "${run_file}" >> "${aggregate_jsonl}"
  done
}

aggregate_all() {
  local prefix="$1"
  local repeats="$2"
  shift 2
  local -a policies=("$@")
  local combined_jsonl="results/${prefix}_combined_all.jsonl"
  local policy

  echo "[INFO] Aggregating run outputs"

  : > "${combined_jsonl}"

  for policy in "${policies[@]}"; do
    aggregate_policy "${prefix}" "${policy}" "${repeats}"
    cat "results/${prefix}_${policy}_all.jsonl" >> "${combined_jsonl}"
  done
}

summarize_aggregate_file() {
  local input_jsonl="$1"
  local output_csv="$2"
  local output_tex="$3"
  local label="$4"

  if [[ ! -f "${input_jsonl}" ]]; then
    echo "[ERROR] Missing aggregate file: ${input_jsonl}" >&2
    return 1
  fi
  if [[ ! -s "${input_jsonl}" ]]; then
    echo "[ERROR] Empty aggregate file: ${input_jsonl}" >&2
    return 1
  fi

  echo "[SUMAG] ${label}"

  python -m benchmark_eval.src.summarize_results \
    --input "${input_jsonl}" \
    --output-csv "${output_csv}" \
    --output-tex "${output_tex}"
}

summarize_aggregates() {
  local prefix="$1"
  shift
  local -a policies=("$@")
  local policy

  echo "[INFO] Summarizing aggregate outputs"

  for policy in "${policies[@]}"; do
    summarize_aggregate_file \
      "results/${prefix}_${policy}_all.jsonl" \
      "results/${prefix}_${policy}_all.csv" \
      "results/${prefix}_${policy}_all.tex" \
      "${policy}"
  done

  summarize_aggregate_file \
    "results/${prefix}_combined_all.jsonl" \
    "results/${prefix}_combined_all.csv" \
    "results/${prefix}_combined_all.tex" \
    "combined"
}

main "$@"
