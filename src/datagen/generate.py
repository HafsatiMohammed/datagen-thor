from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import Draft202012Validator
from tqdm import tqdm

from .clients import OllamaClient, OpenAICompatibleClient
from .io import append_jsonl, read_json, read_text
from .parse import parse_jsonl_response


def make_batches(total: int, batch_size: int) -> list[int]:
    batches = []
    remaining = total
    while remaining > 0:
        n = min(batch_size, remaining)
        batches.append(n)
        remaining -= n
    return batches


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate synthetic JSONL training data.")
    parser.add_argument("--provider", choices=["ollama", "openai"], default="ollama")
    parser.add_argument("--model", default=os.getenv("DATAGEN_MODEL", "qwen3:14b"))
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--system", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--temperature", type=float, default=float(os.getenv("DATAGEN_TEMPERATURE", "0.7")))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("DATAGEN_MAX_TOKENS", "4096")))
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()

    schema = read_json(args.schema)
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
    system = read_text(args.system)
    template = read_text(args.template)
    validator = Draft202012Validator(schema)

    if args.provider == "ollama":
        client = OllamaClient()
    else:
        client = OpenAICompatibleClient()

    out_path = Path(args.out)
    if out_path.exists() and not args.append:
        out_path.unlink()

    generated = 0
    valid = 0

    for batch_n in tqdm(make_batches(args.count, args.batch_size), desc="Generating"):
        prompt = template.format(batch_size=batch_n, schema=schema_text)
        text = client.generate(
            model=args.model,
            prompt=prompt,
            system=system,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        rows = parse_jsonl_response(text)

        good_rows = []
        for row in rows:
            errors = sorted(validator.iter_errors(row), key=lambda e: e.path)
            if not errors:
                good_rows.append(row)

        if good_rows:
            append_jsonl(out_path, good_rows)
            valid += len(good_rows)

        generated += batch_n

    print(f"Requested: {generated}")
    print(f"Valid rows written: {valid}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
