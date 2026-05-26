#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${ROOT_DIR}/bash/state/current.pid"
STATUS_FILE="${ROOT_DIR}/bash/state/current.status"

if [[ ! -f "${PID_FILE}" ]]; then
  echo "No active PID file found."
  exit 0
fi

pid="$(<"${PID_FILE}")"
if kill -0 "${pid}" 2>/dev/null; then
  kill "${pid}"
  echo "Sent SIGTERM to PID ${pid}."
  printf '%s\n' "stopped" > "${STATUS_FILE}"
else
  echo "PID ${pid} is not running."
fi

rm -f "${PID_FILE}"
