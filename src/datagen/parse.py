from __future__ import annotations

import json
import re
from typing import Any


_CODE_FENCE_RE = re.compile(r"```(?:jsonl|json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def strip_code_fences(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def parse_jsonl_response(text: str) -> list[dict[str, Any]]:
    text = strip_code_fences(text)
    rows: list[dict[str, Any]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip().rstrip(",")
        if not line:
            continue
        if line in {"[", "]"}:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)

    if rows:
        return rows

    # Fallback: model may have returned a JSON array.
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]
        if isinstance(obj, dict):
            return [obj]
    except json.JSONDecodeError:
        pass

    return []
