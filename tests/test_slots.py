"""Slot filling: the agent must ask for a missing argument and never invent it."""
from __future__ import annotations

from agent import Agent, new_state
from clinic.responses import say
from clinic.tools import list_appointments


def test_book_without_date_asks_and_books_nothing():
    agent = Agent(offline=True)
    state = new_state("p1")

    result = agent.run_turn(state, "book cardiology")

    assert result.tool_calls == 0
    assert result.reply == say("ask_date", "en")
    assert list_appointments("p1") == []


def test_book_completes_once_date_is_supplied():
    agent = Agent(offline=True)
    state = new_state("p1")

    agent.run_turn(state, "book cardiology")
    result = agent.run_turn(state, "2026-10-10")

    appts = list_appointments("p1")
    assert len(appts) == 1
    assert appts[0]["department"] == "cardiology"
    assert appts[0]["date"] == "2026-10-10"
    assert "book_appointment" in result.tools_used


def test_symptom_without_severity_asks_first():
    agent = Agent(offline=True)
    state = new_state("p1")

    result = agent.run_turn(state, "I have a sore throat")

    assert result.tool_calls == 0
    assert result.reply == say("ask_severity", "en")
