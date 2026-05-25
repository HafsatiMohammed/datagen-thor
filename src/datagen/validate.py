from __future__ import annotations

import argparse
from jsonschema import Draft202012Validator

from .io import read_json, read_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate JSONL against a JSON schema.")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    schema = read_json(args.schema)
    rows = read_jsonl(args.input)
    validator = Draft202012Validator(schema)

    bad = 0
    for idx, row in enumerate(rows, start=1):
        errors = sorted(validator.iter_errors(row), key=lambda e: e.path)
        if errors:
            bad += 1
            print(f"Line {idx}:")
            for error in errors:
                path = ".".join(str(p) for p in error.path) or "<root>"
                print(f"  - {path}: {error.message}")

    print(f"Rows: {len(rows)}")
    print(f"Valid: {len(rows) - bad}")
    print(f"Invalid: {bad}")

    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
