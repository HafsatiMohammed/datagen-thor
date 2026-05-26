#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${ROOT_DIR}/bash/state"
PID_FILE="${STATE_DIR}/current.pid"
STATUS_FILE="${STATE_DIR}/current.status"
RUN_FILE="${STATE_DIR}/current.run"

if [[ ! -f "${RUN_FILE}" ]]; then
  echo "No run metadata found."
  exit 0
fi

# shellcheck source=/dev/null
source "${RUN_FILE}"

echo "Run ID: ${run_id}"
echo "Config: ${config}"
echo "Log: ${log}"
echo "Started: ${started_at}"

if [[ -f "${STATUS_FILE}" ]]; then
  echo "Status: $(<"${STATUS_FILE}")"
fi

if [[ -f "${PID_FILE}" ]]; then
  pid="$(<"${PID_FILE}")"
  if kill -0 "${pid}" 2>/dev/null; then
    echo "PID: ${pid} (running)"
    ps -p "${pid}" -o pid=,etime=,cmd=
  else
    echo "PID: ${pid} (not running)"
  fi
else
  echo "PID: none"
fi

if [[ -f "${log}" ]]; then
  echo
  echo "Last log lines:"
  tail -n 20 "${log}"
fi
