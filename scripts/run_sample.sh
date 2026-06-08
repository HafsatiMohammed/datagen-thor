#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

python -m datagen.generate \
  --provider ollama \
  --model "${1:-qwen3:14b}" \
  --count "${2:-100}" \
  --batch-size "${3:-10}" \
  --language "${4:-English}" \
  --class-ratios 'complete=0.35,incomplete=0.25,abandoned=0.15,correction_in_progress=0.15,unclear=0.10' \
  --schema schemas/example_schema_endOfsentence.json \
  --system prompts/system_endOfsentence.txt \
  --template prompts/user_template_endOfsentence.txt \
  --out outputs/sample.endofturn.jsonl

python -m datagen.validate \
  --schema schemas/example_schema_endOfsentence.json \
  --input outputs/sample.endofturn.jsonl

python -m datagen.dedupe \
  --input outputs/sample.endofturn.jsonl \
  --output outputs/sample.endofturn.deduped.jsonl
