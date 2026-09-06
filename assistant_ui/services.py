"""Mock service layer for the frontend.

This module provides deterministic demo responses so the UI can be
demonstrated before backend integration. It intentionally does NOT import
any backend modules (agent, graph, clinic.tools, clinic.state, etc.).

In COMMIT 2, replace these functions with real calls to the backend.
"""
from __future__ import annotations

from datetime import date, timedelta

# Demo patient ID used for mock data
_DEMO_PATIENT_ID = "P001"

# Deterministic demo appointments
_DEMO_APPOINTMENTS = [
    {
        "id": "APPT-1",
        "patient_id": _DEMO_PATIENT_ID,
        "department": "cardiology",
        "date": (date.today() + timedelta(days=3)).isoformat(),
        "booked_at": "2026-01-10T10:00:00+00:00",
    },
    {
        "id": "APPT-2",
        "patient_id": _DEMO_PATIENT_ID,
        "department": "dermatology",
        "date": (date.today() + timedelta(days=10)).isoformat(),
        "booked_at": "2026-01-11T14:30:00+00:00",
    },
]


def log_symptom(patient_id: str, symptom: str, severity: int) -> dict:
    """Mock implementation of log_symptom.

    Returns a deterministic demo record without persisting anything.
    """
    return {
        "id": "SYMP-DEMO",
        "patient_id": patient_id,
        "symptom": symptom,
        "severity": severity,
        "logged_at": "2026-01-12T08:00:00+00:00",
    }


def book_appointment(patient_id: str, department: str, date_str: str) -> dict:
    """Mock implementation of book_appointment.

    Returns a deterministic demo record without persisting anything.
    """
    return {
        "id": "APPT-DEMO",
        "patient_id": patient_id,
        "department": department,
        "date": date_str,
        "booked_at": "2026-01-12T08:05:00+00:00",
        "duplicate": False,
    }


def list_appointments(patient_id: str) -> list[dict]:
    """Mock implementation of list_appointments.

    Returns demo appointments filtered by patient_id.
    """
    return [a for a in _DEMO_APPOINTMENTS if a["patient_id"] == patient_id]


def chat(message: str, patient_id: str) -> str:
    """Return a simple demo response based on the user's message.

    This is intentionally naive; it exists only to make the chat UI feel
    alive during the frontend-only commit.
    """
    lowered = message.lower()

    # Check for listing appointments first (before booking)
    if any(phrase in lowered for phrase in ["show my appointments", "list appointments", "my appointments", "upcoming appointments"]):
        return "Demo: your appointments would be listed here once connected."

    # Check for booking appointments
    if any(phrase in lowered for phrase in ["book an appointment", "book me", "schedule an appointment"]) or ("appointment" in lowered and "book" in lowered):
        return (
            "Demo: your appointment would be booked here once the frontend is "
            "connected to the backend."
        )

    # Check for symptom logging
    if "symptom" in lowered or "log" in lowered:
        return (
            "Demo: your symptom would be logged here once the frontend is "
            "connected to the backend."
        )

    return (
        "Hi! I can log a symptom, book an appointment, or show your appointments. "
        "This is a demo response; backend integration is coming in COMMIT 2."
    )
