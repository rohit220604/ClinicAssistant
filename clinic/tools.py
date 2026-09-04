"""The three functions the assignment fixes as a contract.

They are deliberately plain: validate input, touch the JSON store, return a
dict. No LLM, no I/O beyond the store, so they are trivial to unit-test and the
graders can call them directly.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from clinic.storage import load_store, next_id, save_store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_iso_date(value: str) -> str:
    try:
        # Accepts YYYY-MM-DD. Raises ValueError on anything else.
        date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"date must be an ISO date like 2026-01-31, got {value!r}")
    return value


def log_symptom(patient_id: str, symptom: str, severity: int) -> dict:
    if not patient_id:
        raise ValueError("patient_id is required")
    if not symptom or not symptom.strip():
        raise ValueError("symptom text is required")
    if not isinstance(severity, int) or isinstance(severity, bool):
        raise ValueError("severity must be an integer 1-5")
    if not 1 <= severity <= 5:
        raise ValueError("severity must be between 1 and 5")

    store = load_store()
    record = {
        "id": next_id(store["symptoms"], "SYMP"),
        "patient_id": patient_id,
        "symptom": symptom.strip(),
        "severity": severity,
        "logged_at": _now(),
    }
    store["symptoms"].append(record)
    save_store(store)
    return record


def book_appointment(patient_id: str, department: str, date: str) -> dict:
    if not patient_id:
        raise ValueError("patient_id is required")
    if not department or not department.strip():
        raise ValueError("department is required")
    date = _require_iso_date(date)
    department = department.strip().lower()

    store = load_store()
    # Idempotency: the same patient/department/date is one appointment, even if
    # the message arrives twice (e.g. a webhook retry). We return the existing
    # one instead of creating a duplicate.
    dedupe_key = f"{patient_id}|{department}|{date}"
    for appt in store["appointments"]:
        if appt.get("key") == dedupe_key:
            return {**appt, "duplicate": True}

    record = {
        "id": next_id(store["appointments"], "APPT"),
        "patient_id": patient_id,
        "department": department,
        "date": date,
        "key": dedupe_key,
        "booked_at": _now(),
    }
    store["appointments"].append(record)
    save_store(store)
    return {**record, "duplicate": False}


def list_appointments(patient_id: str) -> list[dict]:
    if not patient_id:
        raise ValueError("patient_id is required")
    store = load_store()
    mine = [a for a in store["appointments"] if a["patient_id"] == patient_id]
    return sorted(mine, key=lambda a: a["date"])
