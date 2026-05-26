#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 bash/config/generate.conf" >&2
  exit 1
fi

CONFIG_FILE="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="${ROOT_DIR}/bash/run_generation_batch.sh"
STATE_DIR="${ROOT_DIR}/bash/state"
PID_FILE="${STATE_DIR}/current.pid"

mkdir -p "${STATE_DIR}"

if [[ -f "${PID_FILE}" ]]; then
  existing_pid="$(<"${PID_FILE}")"
  if kill -0 "${existing_pid}" 2>/dev/null; then
    echo "A generation run is already active with PID ${existing_pid}."
    echo "Use bash/monitor_generation.sh to inspect it."
    exit 1
  fi
  rm -f "${PID_FILE}"
fi

nohup "${RUNNER}" "${CONFIG_FILE}" >/dev/null 2>&1 &
new_pid="$!"

echo "Started detached generation run."
echo "PID: ${new_pid}"
echo "Config: ${CONFIG_FILE}"
echo "Monitor: bash/monitor_generation.sh"
