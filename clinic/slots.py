"""Pulling structured slots out of free text.

Used by the offline stub to fill tool arguments deterministically, and handy for
light validation. Every function returns None when it isn't sure - it never
guesses, because a guessed argument is exactly what the assignment forbids.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

DEPARTMENTS = [
    "cardiology", "dermatology", "pediatrics", "paediatrics", "orthopedics",
    "orthopaedics", "gynaecology", "gynecology", "ent", "dental", "neurology",
    "psychiatry", "ophthalmology", "physiotherapy", "oncology", "urology",
    "general", "general medicine",
]

_ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_SEVERITY_LABELLED = re.compile(r"(?:severity|level|scale|pain)\D{0,6}([1-5])\b")
_SEVERITY_BARE = re.compile(r"^\s*([1-5])\s*$")

_RELATIVE = {
    "today": 0, "aaj": 0, "आज": 0,
    "tomorrow": 1, "kal": 1, "कल": 1,
    "day after tomorrow": 2, "parso": 2, "parson": 2, "परसों": 2,
}


def find_department(text: str) -> str | None:
    low = text.lower()
    for dept in DEPARTMENTS:
        if re.search(rf"\b{re.escape(dept)}\b", low):
            return "general medicine" if dept == "general" else dept
    return None


def find_date(text: str, today: date | None = None) -> str | None:
    m = _ISO.search(text)
    if m:
        return m.group(1)
    today = today or date.today()
    low = text.lower()
    # Longest phrases first so "day after tomorrow" wins over "tomorrow".
    for phrase in sorted(_RELATIVE, key=len, reverse=True):
        if phrase in low:
            return (today + timedelta(days=_RELATIVE[phrase])).isoformat()
    return None


def find_severity(text: str) -> int | None:
    m = _SEVERITY_LABELLED.search(text.lower())
    if m:
        return int(m.group(1))

    m = _SEVERITY_BARE.match(text)
    return int(m.group(1)) if m else None
