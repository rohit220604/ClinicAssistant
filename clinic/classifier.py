"""Intent classification with a keyword fast-path.

Mirrors the safety gate's shape: try the deterministic keyword router first, and
only fall back to the model when the keywords are unsure. This is the same
pre-router that saves LLM calls in Part 5.
"""
from __future__ import annotations

from clinic.rules import keyword_intent


def classify_intent(message: str, client, use_keyword: bool = True) -> str:
    if use_keyword:
        guess = keyword_intent(message)
        if guess is not None:
            return guess
    return client.classify(message, "intent")
