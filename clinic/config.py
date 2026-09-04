"""Central place for settings and file paths.

Everything that reads the environment lives here so the rest of the code can
just import `settings` and never touch os.environ directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project layout
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"

STORE_PATH = DATA_DIR / "clinic_store.json"
LATENCY_LOG = LOG_DIR / "latency.jsonl"
SAFETY_LOG = LOG_DIR / "safety.jsonl"


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    chat_model: str
    classifier_model: str
    classifier_timeout: int
    max_tool_calls: int

    @property
    def has_key(self) -> bool:
        return bool(self.api_key) and self.api_key != "your_key_here"


def load_settings() -> Settings:
    return Settings(
        api_key=os.environ.get("GROQ_API_KEY"),
        chat_model=os.environ.get("CLINIC_CHAT_MODEL", "llama-3.3-70b-versatile"),
        classifier_model=os.environ.get("CLINIC_CLASSIFIER_MODEL", "llama-3.1-8b-instant"),
        classifier_timeout=_int_env("CLINIC_CLASSIFIER_TIMEOUT", 6),
        max_tool_calls=_int_env("CLINIC_MAX_TOOL_CALLS", 4),
    )


settings = load_settings()
