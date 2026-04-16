"""Helpers for reading and writing JSONL files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSON Lines file into memory."""
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: Iterable[dict]) -> None:
    """Write records to a JSON Lines file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
