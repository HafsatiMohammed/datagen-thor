from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import Draft202012Validator
from tqdm import tqdm

from .clients import OllamaClient, OpenAICompatibleClient
from .io import append_jsonl, read_json, read_jsonl, read_text
from .parse import parse_jsonl_response


def parse_class_ratios(spec: str, allowed_classes: list[str]) -> dict[str, float]:
    ratios: dict[str, float] = {}
    for item in spec.split(","):
        part = item.strip()
        if not part:
            continue
        key, sep, value = part.partition("=")
        if sep != "=":
            raise ValueError(f"Invalid class ratio '{part}'. Use interruption_class=weight.")
        class_name = key.strip()
        if class_name not in allowed_classes:
            raise ValueError(f"Unknown interruption_class '{class_name}'. Allowed values: {', '.join(allowed_classes)}")
        try:
            weight = float(value.strip())
        except ValueError as exc:
            raise ValueError(f"Invalid weight for '{class_name}': {value.strip()}") from exc
        if weight < 0:
            raise ValueError(f"Weight for '{class_name}' must be non-negative.")
        ratios[class_name] = weight

    missing = [class_name for class_name in allowed_classes if class_name not in ratios]
    if missing:
        raise ValueError(
            "Missing class ratios for: " + ", ".join(missing) + ". "
            "Specify all classes, for example continue=0.2,stop=0.2,pause=0.2,clarify_or_repeat=0.2,change_or_correct=0.2"
        )

    if sum(ratios.values()) <= 0:
        raise ValueError("Class ratios must have a positive total.")

    return ratios


def resolve_requested_language(requested_language: str, allowed_languages: list[str]) -> str:
    if requested_language.strip().lower() == "multilingual":
        return "multilingual"

    normalized = {language.lower(): language for language in allowed_languages}
    key = requested_language.strip().lower()
    if key not in normalized:
        raise ValueError(
            f"Unknown language '{requested_language}'. Allowed values: multilingual, "
            + ", ".join(allowed_languages)
        )
    return normalized[key]


def allocate_counts(total: int, weights: dict[str, float], ordered_keys: list[str]) -> dict[str, int]:
    if total <= 0:
        return {key: 0 for key in ordered_keys}

    weight_total = sum(weights[key] for key in ordered_keys)
    raw = {key: total * weights[key] / weight_total for key in ordered_keys}
    counts = {key: int(raw[key]) for key in ordered_keys}
    remainder = total - sum(counts.values())

    if remainder > 0:
        ranked = sorted(
            ordered_keys,
            key=lambda key: (raw[key] - counts[key], -ordered_keys.index(key)),
            reverse=True,
        )
        for key in ranked[:remainder]:
            counts[key] += 1

    return counts


def format_class_distribution(counts: dict[str, int]) -> str:
    return "\n".join(f"- {class_name}: {count}" for class_name, count in counts.items())


def filter_rows_to_class_targets(rows: list[dict], class_targets: dict[str, int]) -> list[dict]:
    accepted: list[dict] = []
    seen = {class_name: 0 for class_name in class_targets}

    for row in rows:
        class_name = row.get("interruption_class")
        if class_name not in class_targets:
            continue
        if seen[class_name] >= class_targets[class_name]:
            continue
        accepted.append(row)
        seen[class_name] += 1

    return accepted


def filter_rows_to_language(rows: list[dict], requested_language: str) -> list[dict]:
    if requested_language.strip().lower() == "multilingual":
        return rows

    return [row for row in rows if row.get("language") == requested_language]


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
    parser.add_argument(
        "--language",
        default="multilingual",
        help="Language to use for generation, for example 'English', 'French', or 'multilingual'.",
    )
    parser.add_argument(
        "--class-ratios",
        help=(
            "Comma-separated interruption_class weights, for example "
            "'continue=0.4,stop=0.2,pause=0.15,clarify_or_repeat=0.15,change_or_correct=0.1'."
        ),
    )
    parser.add_argument("--temperature", type=float, default=float(os.getenv("DATAGEN_TEMPERATURE", "0.7")))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("DATAGEN_MAX_TOKENS", "4096")))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--append", action="store_true", help="Append --count new rows to an existing output file.")
    mode.add_argument(
        "--resume",
        action="store_true",
        help="Continue an existing output file until it reaches --count total rows.",
    )
    args = parser.parse_args()

    schema = read_json(args.schema)
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
    system = read_text(args.system)
    template = read_text(args.template)
    validator = Draft202012Validator(schema)
    allowed_classes = schema["properties"]["interruption_class"]["enum"]
    allowed_languages = schema["properties"]["language"]["enum"]
    args.language = resolve_requested_language(args.language, allowed_languages)
    class_ratios = parse_class_ratios(args.class_ratios, allowed_classes) if args.class_ratios else None

    if args.provider == "ollama":
        client = OllamaClient()
    else:
        client = OpenAICompatibleClient()

    out_path = Path(args.out)
    existing_rows = 0
    existing_class_counts = {class_name: 0 for class_name in allowed_classes}
    if out_path.exists():
        if args.resume:
            existing_data = read_jsonl(out_path)
            existing_rows = len(existing_data)
            for row in existing_data:
                class_name = row.get("interruption_class")
                if class_name in existing_class_counts:
                    existing_class_counts[class_name] += 1
        elif not args.append:
            out_path.unlink()

    target_count = args.count
    if args.resume:
        if existing_rows >= target_count:
            print(f"Existing rows: {existing_rows}")
            print(f"Requested total: {target_count}")
            print("Nothing to do: output already meets or exceeds requested count.")
            print(f"Output: {out_path}")
            return
        target_count -= existing_rows

    remaining_class_counts: dict[str, int] | None = None
    if class_ratios:
        if args.resume:
            total_class_targets = allocate_counts(args.count, class_ratios, allowed_classes)
            over_target = [
                class_name
                for class_name in allowed_classes
                if existing_class_counts[class_name] > total_class_targets[class_name]
            ]
            if over_target:
                details = ", ".join(
                    f"{class_name}={existing_class_counts[class_name]}/{total_class_targets[class_name]}"
                    for class_name in over_target
                )
                raise ValueError(
                    "Cannot resume to the requested class ratios because existing rows already exceed target counts for: "
                    + details
                )
            remaining_class_counts = {
                class_name: total_class_targets[class_name] - existing_class_counts[class_name]
                for class_name in allowed_classes
            }
        else:
            remaining_class_counts = allocate_counts(target_count, class_ratios, allowed_classes)

    generated = 0
    valid = existing_rows if args.resume else 0
    remaining_total = sum(remaining_class_counts.values()) if remaining_class_counts else target_count
    requested_this_run = remaining_total
    max_attempts = max(3, len(make_batches(max(remaining_total, 1), args.batch_size)) * 3)
    attempts = 0

    with tqdm(total=requested_this_run, desc="Generating") as progress:
        while remaining_total > 0 and attempts < max_attempts:
            batch_n = min(args.batch_size, remaining_total)
            if remaining_class_counts:
                batch_class_targets = allocate_counts(batch_n, remaining_class_counts, allowed_classes)
                class_distribution = format_class_distribution(batch_class_targets)
            else:
                batch_class_targets = None
                class_distribution = "- Balance interruption_class values naturally across the batch."

            prompt = template.format(
                batch_size=batch_n,
                schema=schema_text,
                language=args.language,
                class_distribution=class_distribution,
            )
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

            good_rows = filter_rows_to_language(good_rows, args.language)

            if batch_class_targets:
                good_rows = filter_rows_to_class_targets(good_rows, batch_class_targets)

            if not batch_class_targets:
                good_rows = good_rows[:batch_n]

            if good_rows:
                append_jsonl(out_path, good_rows)
                valid += len(good_rows)
                remaining_total -= len(good_rows)
                progress.update(len(good_rows))
                if remaining_class_counts:
                    for row in good_rows:
                        remaining_class_counts[row["interruption_class"]] -= 1

            generated += batch_n
            attempts += 1

    if args.resume:
        print(f"Existing rows: {existing_rows}")
        print(f"Requested total: {args.count}")
        print(f"Requested this run: {generated}")
    else:
        print(f"Requested: {generated}")
    print(f"Valid rows written: {valid}")
    if remaining_total > 0:
        print(f"Rows still missing after retries: {remaining_total}")
    if remaining_class_counts:
        print("Remaining class targets: " + ", ".join(f"{key}={value}" for key, value in remaining_class_counts.items()))
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
