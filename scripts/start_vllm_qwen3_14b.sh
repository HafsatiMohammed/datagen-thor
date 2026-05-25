#!/usr/bin/env bash
set -euo pipefail

python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-14B \
  --host 0.0.0.0 \
  --port 8000
