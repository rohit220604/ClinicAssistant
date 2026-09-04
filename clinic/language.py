"""Language detection and script checks.

We only need to tell three things apart: English, Hindi in Devanagari, and
Hinglish (Hindi written in Latin letters). A full language model is overkill for
that, so this is deliberately a small heuristic:

  - any Devanagari character  -> "hi"
  - else common romanized-Hindi markers present -> "hinglish"
  - else -> "en"
"""
from __future__ import annotations

import re

DEVANAGARI = re.compile(r"[\u0900-\u097F]")
LATIN_WORD = re.compile(r"[A-Za-z]{2,}")

# A short list of everyday Hinglish tokens. Kept to words that are distinctly
# Hindi - English words like "book" or "doctor" are deliberately excluded so a
# plain English sentence isn't misread as Hinglish.
HINGLISH_MARKERS = {
    "hai", "haan", "nahi", "nahin", "kya", "kyaa", "kaise", "kaisa", "mujhe",
    "mera", "meri", "mere", "aap", "aapka", "chahiye", "karna", "karni", "karo",
    "krna", "krni", "krwana", "dard", "bukhar", "bukhaar", "tabiyat",
    "seene", "saans", "saas", "sardi", "khansi", "raha", "rahi", "gaya",
    "aaj", "kal", "abhi", "dikhana", "hoon", "thodi", "bahut", "bohot",
    "ilaj", "ilaaj", "dawa", "kripya", "batayein", "karoon",
}


def has_devanagari(text: str) -> bool:
    return bool(DEVANAGARI.search(text))


def detect_language(text: str) -> str:
    if has_devanagari(text):
        return "hi"
    tokens = re.findall(r"[a-z]+", text.lower())
    if any(tok in HINGLISH_MARKERS for tok in tokens):
        return "hinglish"
    return "en"


def has_latin_words(text: str) -> bool:
    """True if the text contains Latin-alphabet words (len >= 2)."""
    return bool(LATIN_WORD.search(text))


def script_purity_ok(reply: str, lang: str) -> bool:
    """Stretch A check: a reply meant to be in Devanagari must not fall back to
    romanized Latin ("aap" where it should be "आप"). Digits and punctuation are
    fine; a run of Latin letters is the leak we care about.
    """
    if lang != "hi":
        return True
    return not has_latin_words(reply)
