from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from .io import read_jsonl


_SPACE_RE = re.compile(r"\s+")


def normalize(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True).lower()
    return _SPACE_RE.sub(" ", text).strip()


def fingerprint(row: dict) -> str:
    return hashlib.sha256(normalize(row).encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicate JSONL rows exactly after normalization.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = read_jsonl(args.input)
    seen = set()
    kept = []

    for row in rows:
        fp = fingerprint(row)
        if fp not in seen:
            seen.add(fp)
            kept.append(row)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in kept:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Input rows: {len(rows)}")
    print(f"Output rows: {len(kept)}")
    print(f"Removed duplicates: {len(rows) - len(kept)}")


if __name__ == "__main__":
    main()
