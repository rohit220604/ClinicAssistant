"""Latency logging and percentile maths.

We append one JSON line per LLM call and one per turn to a JSONL file, then read
it back to report p50/p95. Percentiles, not the mean, because the mean hides the
slow tail that actually annoys patients.
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from pathlib import Path

from clinic.config import LATENCY_LOG


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@contextmanager
def stopwatch():
    """Yields a callable returning elapsed milliseconds so far."""
    start = time.perf_counter()
    yield lambda: (time.perf_counter() - start) * 1000


def log_llm_call(ms: float, model: str, kind: str, path: Path = LATENCY_LOG) -> None:
    append_jsonl(path, {"ts": time.time(), "event": "llm_call", "kind": kind, "model": model, "ms": round(ms, 2)})


def log_turn(turn_ms: float, llm_calls: int, offline: bool, path: Path = LATENCY_LOG) -> None:
    append_jsonl(path, {"ts": time.time(), "event": "turn", "ms": round(turn_ms, 2), "llm_calls": llm_calls, "offline": offline})


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (p / 100) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac


def summarise(path: Path = LATENCY_LOG) -> dict:
    rows = read_jsonl(path)
    turns = [r["ms"] for r in rows if r.get("event") == "turn"]
    calls = [r["ms"] for r in rows if r.get("event") == "llm_call"]
    per_turn_calls = [r["llm_calls"] for r in rows if r.get("event") == "turn"]
    return {
        "turns": len(turns),
        "turn_p50": round(percentile(turns, 50), 2),
        "turn_p95": round(percentile(turns, 95), 2),
        "llm_p50": round(percentile(calls, 50), 2),
        "llm_p95": round(percentile(calls, 95), 2),
        "avg_llm_calls_per_turn": round(sum(per_turn_calls) / len(per_turn_calls), 2) if per_turn_calls else 0.0,
    }
