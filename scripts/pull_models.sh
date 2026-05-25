#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-qwen3:14b}"
ollama pull "$MODEL"
ollama list
