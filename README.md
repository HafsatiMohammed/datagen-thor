# datagen-thor

Small local synthetic text/data generation project for Thor.

Default path:
- **Ollama** for quick setup and local generation.
- Optional **vLLM/OpenAI-compatible server** for higher-throughput batching later.


## 1. Create Python env

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## 2. Install Ollama on Thor

```bash
bash scripts/install_ollama.sh
```

Verify:

```bash
ollama -v
sudo systemctl status ollama --no-pager
```

## 3. Pull a model

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

## 4. Configure

```bash
cp .env.example .env
```

Edit `.env` if needed.

## 5. Run sample generation

```bash
source .venv/bin/activate
python -m datagen.generate \
  --provider ollama \
  --model qwen3:14b \
  --count 100 \
  --batch-size 10 \
  --language English \
  --class-ratios 'complete=0.35,incomplete=0.25,abandoned=0.15,correction_in_progress=0.15,unclear=0.10' \
  --schema schemas/example_schema_endOfsentence.json \
  --system prompts/system_endOfsentence.txt \
  --template prompts/user_template_endOfsentence.txt \
  --out outputs/sample.endofturn.jsonl
```

Resume generation into the same file until it reaches a target total row count:

```bash
python -m datagen.generate \
  --provider ollama \
  --model qwen3:14b \
  --count 100 \
  --batch-size 10 \
  --language English \
  --class-ratios 'complete=0.35,incomplete=0.25,abandoned=0.15,correction_in_progress=0.15,unclear=0.10' \
  --schema schemas/example_schema_endOfsentence.json \
  --system prompts/system_endOfsentence.txt \
  --template prompts/user_template_endOfsentence.txt \
  --out outputs/sample.endofturn.jsonl \
  --resume
```

Use `--append` if you want to add `--count` more rows regardless of how many already exist.
Use `--language` to control the generated language, for example `English`, `French`, `Arabic`, or `multilingual`.
Use `--class-ratios` to control the `completion_class` mix, for example:

```bash
python -m datagen.generate \
  --provider ollama \
  --model qwen3:14b \
  --count 100 \
  --batch-size 10 \
  --language English \
  --class-ratios 'complete=0.35,incomplete=0.25,abandoned=0.15,correction_in_progress=0.15,unclear=0.10' \
  --schema schemas/example_schema_endOfsentence.json \
  --system prompts/system_endOfsentence.txt \
  --template prompts/user_template_endOfsentence.txt \
  --out outputs/sample.endofturn.jsonl
```

Ratios are converted into exact row targets across the requested count. In `--resume` mode, existing rows are taken into account.

## Config-driven detached runs

Edit the config file:

```bash
bash/config/generate.conf
```

The config controls:
- `BATCH_SIZE`
- `LANGUAGES`
- `COUNTS` per language
- `CLASS_RATIOS` per language
- `OUTPUT_FILES` per language
- shared model, schema, prompt, and mode settings

Start a detached run that keeps going after you close the terminal:

```bash
bash bash/start_generation.sh bash/config/generate.conf
```

Monitor the active run:

```bash
bash bash/monitor_generation.sh
```

Stop the active run:

```bash
bash bash/stop_generation.sh
```

Runtime files:
- Logs are written under `bash/logs/`
- PID and status files are written under `bash/state/`

Validate and dedupe:

```bash
python -m datagen.validate --schema schemas/example_schema_endOfsentence.json --input outputs/sample.endofturn.jsonl
python -m datagen.dedupe --input outputs/sample.endofturn.jsonl --output outputs/sample.endofturn.deduped.jsonl
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
  --language English \
  --class-ratios 'complete=0.35,incomplete=0.25,abandoned=0.15,correction_in_progress=0.15,unclear=0.10' \
  --schema schemas/example_schema_endOfsentence.json \
  --system prompts/system_endOfsentence.txt \
  --template prompts/user_template_endOfsentence.txt \
  --out outputs/sample.endofturn.vllm.jsonl
```

## Output contract

The generator asks the model to return JSONL, one object per line. Each row must validate against `schemas/example_schema_endOfsentence.json`.

Default row shape:

```json
{
  "input": "set a timer for ten minutes",
  "output": "Send the transcript to the LLM.",
  "completion_class": "complete|incomplete|abandoned|correction_in_progress|unclear",
  "language": "English|French|Arabic|...",
  "category": "home_assistant|navigation|robot_command|reminder|messaging|search|scheduling|conversation|general",
  "difficulty": "easy|medium|hard"
}
```

## Tips

- Start with `--count 100`, inspect quality, then scale.
- Keep temperature around `0.7` for diversity.
- Use `--batch-size 5` or `10` if the model starts producing malformed JSON.
- Generate more than needed, then dedupe and filter.
