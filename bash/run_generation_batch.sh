#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 bash/config/generate.conf" >&2
  exit 1
fi

CONFIG_FILE="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=/dev/null
source "${ROOT_DIR}/${CONFIG_FILE}"

mkdir -p "${ROOT_DIR}/${LOG_DIR}" "${ROOT_DIR}/${STATE_DIR}"

RUN_ID="$(date +%Y%m%d-%H%M%S)"
RUN_LOG="${ROOT_DIR}/${LOG_DIR}/run-${RUN_ID}.log"
PID_FILE="${ROOT_DIR}/${STATE_DIR}/current.pid"
STATUS_FILE="${ROOT_DIR}/${STATE_DIR}/current.status"
RUN_FILE="${ROOT_DIR}/${STATE_DIR}/current.run"

if [[ ${#LANGUAGES[@]} -eq 0 ]]; then
  echo "No languages configured." >&2
  exit 1
fi

if [[ ${#LANGUAGES[@]} -ne ${#COUNTS[@]} ]] || [[ ${#LANGUAGES[@]} -ne ${#CLASS_RATIOS[@]} ]] || [[ ${#LANGUAGES[@]} -ne ${#OUTPUT_FILES[@]} ]]; then
  echo "LANGUAGES, COUNTS, CLASS_RATIOS, and OUTPUT_FILES must have the same length." >&2
  exit 1
fi

write_status() {
  printf '%s\n' "$1" > "${STATUS_FILE}"
}

touch "${RUN_LOG}"
printf '%s\n' "$$" > "${PID_FILE}"
{
  echo "run_id=${RUN_ID}"
  echo "config=${CONFIG_FILE}"
  echo "log=${RUN_LOG}"
  echo "started_at=$(date --iso-8601=seconds)"
} > "${RUN_FILE}"

write_status "starting"

cleanup() {
  rm -f "${PID_FILE}"
}

trap cleanup EXIT

on_error() {
  write_status "failed"
}

trap on_error ERR

for i in "${!LANGUAGES[@]}"; do
  language="${LANGUAGES[$i]}"
  count="${COUNTS[$i]}"
  ratios="${CLASS_RATIOS[$i]}"
  output_file="${OUTPUT_FILES[$i]}"
  output_dir="$(dirname "${ROOT_DIR}/${output_file}")"
  current_job=$((i + 1))
  total_jobs="${#LANGUAGES[@]}"

  mkdir -p "${output_dir}"

  mode_flag=()
  case "${MODE}" in
    overwrite)
      mode_flag=()
      ;;
    resume)
      mode_flag=(--resume)
      ;;
    append)
      mode_flag=(--append)
      ;;
    *)
      echo "Invalid MODE='${MODE}'. Use overwrite, resume, or append." | tee -a "${RUN_LOG}" >&2
      write_status "failed: invalid mode"
      exit 1
      ;;
  esac

  write_status "running ${language} (${current_job}/${total_jobs})"
  {
    echo "[$(date --iso-8601=seconds)] Starting language=${language} count=${count} output=${output_file}"
    echo "[$(date --iso-8601=seconds)] Ratios=${ratios}"
  } >> "${RUN_LOG}"

  "${ROOT_DIR}/${PYTHON_BIN}" -m datagen.generate \
    --provider "${PROVIDER}" \
    --model "${MODEL}" \
    --count "${count}" \
    --batch-size "${BATCH_SIZE}" \
    --language "${language}" \
    --class-ratios "${ratios}" \
    --schema "${ROOT_DIR}/${SCHEMA}" \
    --system "${ROOT_DIR}/${SYSTEM_PROMPT}" \
    --template "${ROOT_DIR}/${USER_TEMPLATE}" \
    --out "${ROOT_DIR}/${output_file}" \
    "${mode_flag[@]}" >> "${RUN_LOG}" 2>&1

  echo "[$(date --iso-8601=seconds)] Finished language=${language}" >> "${RUN_LOG}"
done

write_status "completed"
echo "[$(date --iso-8601=seconds)] Run completed successfully." >> "${RUN_LOG}"
