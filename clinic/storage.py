"""Single-JSON-file persistence.

The whole store is one dict with two lists. We read it, hand back a copy, and
write it back atomically (temp file + replace) so a crash mid-write can't leave
a half-written file behind.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from clinic.config import STORE_PATH

EMPTY_STORE: dict[str, list] = {"symptoms": [], "appointments": []}


def load_store(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = STORE_PATH

    if not path.exists():
        return {"symptoms": [], "appointments": []}
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    # Be forgiving if the file predates a key we now expect.
    for key, default in EMPTY_STORE.items():
        data.setdefault(key, list(default))
    return data


def save_store(data: dict[str, Any], path: Path | None = None) -> None:
    if path is None:
        path = STORE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def next_id(items: list[dict], prefix: str) -> str:
    """Small, human-readable ids like SYMP-1, APPT-4."""
    return f"{prefix}-{len(items) + 1}"
