"""Stretch B - idempotency.

A retried message (same patient, department, date) must not create a second
appointment. Proven with a test, not just asserted in the README.
"""
from __future__ import annotations

from agent import Agent, new_state
from clinic.tools import book_appointment, list_appointments


def test_double_book_same_slot_is_one_appointment():
    first = book_appointment("p1", "cardiology", "2026-11-05")
    second = book_appointment("p1", "cardiology", "2026-11-05")

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert first["id"] == second["id"]
    assert len(list_appointments("p1")) == 1


def test_retried_message_does_not_double_book():
    # Simulate a webhook delivering the same message twice - two fresh sessions.
    message = "book me for dermatology on 2026-11-05"
    for _ in range(2):
        Agent(offline=True).run_turn(new_state("p9"), message)

    assert len(list_appointments("p9")) == 1


def test_different_date_is_a_separate_appointment():
    book_appointment("p1", "cardiology", "2026-11-05")
    book_appointment("p1", "cardiology", "2026-11-06")

    assert len(list_appointments("p1")) == 2
