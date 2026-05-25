#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

python -m datagen.generate \
  --provider ollama \
  --model "${1:-qwen3:14b}" \
  --count "${2:-100}" \
  --batch-size "${3:-10}" \
  --schema schemas/example_schema.json \
  --system prompts/system.txt \
  --template prompts/user_template.txt \
  --out outputs/sample.jsonl

python -m datagen.validate \
  --schema schemas/example_schema.json \
  --input outputs/sample.jsonl

python -m datagen.dedupe \
  --input outputs/sample.jsonl \
  --output outputs/sample.deduped.jsonl
