# datagen-thor

Small local synthetic text/data generation project for Thor.

Default path:
- **Ollama** for quick setup and local generation.
- Optional **vLLM/OpenAI-compatible server** for higher-throughput batching later.

## 1. Unzip on Thor

```bash
unzip datagen-thor.zip
cd datagen-thor
```

## 2. Create Python env

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## 3. Install Ollama on Thor

```bash
bash scripts/install_ollama.sh
```

Verify:

```bash
ollama -v
sudo systemctl status ollama --no-pager
```

## 4. Pull a model

Recommended default:

```bash
ollama pull qwen3:14b
```

Faster, lower quality:

```bash
ollama pull phi4-mini
```

If a model tag is not available in your Ollama registry, run:

```bash
ollama list
ollama pull qwen2.5:14b-instruct
```

## 5. Configure

```bash
cp .env.example .env
```

Edit `.env` if needed.

## 6. Run sample generation

```bash
source .venv/bin/activate
python -m datagen.generate \
  --provider ollama \
  --model qwen3:14b \
  --count 100 \
  --batch-size 10 \
  --schema schemas/example_schema.json \
  --system prompts/system.txt \
  --template prompts/user_template.txt \
  --out outputs/sample.jsonl
```

Validate and dedupe:

```bash
python -m datagen.validate --schema schemas/example_schema.json --input outputs/sample.jsonl
python -m datagen.dedupe --input outputs/sample.jsonl --output outputs/sample.deduped.jsonl
```

## vLLM option

For higher throughput, run an OpenAI-compatible server with vLLM, then use `--provider openai`.

Example server:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-14B \
  --host 0.0.0.0 \
  --port 8000
```

Then generate:

```bash
OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=EMPTY \
python -m datagen.generate \
  --provider openai \
  --model Qwen/Qwen3-14B \
  --count 100 \
  --batch-size 10 \
  --schema schemas/example_schema.json \
  --system prompts/system.txt \
  --template prompts/user_template.txt \
  --out outputs/sample.vllm.jsonl
```

## Output contract

The generator asks the model to return JSONL, one object per line. Each row must validate against `schemas/example_schema.json`.

Default row shape:

```json
{
  "input": "user text",
  "output": "ideal answer",
  "category": "support|sales|robotics|general",
  "difficulty": "easy|medium|hard"
}
```

## Tips

- Start with `--count 100`, inspect quality, then scale.
- Keep temperature around `0.7` for diversity.
- Use `--batch-size 5` or `10` if the model starts producing malformed JSON.
- Generate more than needed, then dedupe and filter.
