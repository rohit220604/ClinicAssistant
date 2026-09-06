"""Regression tests for the offline stub's multi-turn handling.

These cover bugs where a fresh message inherited intent/slots from earlier in the
same session (e.g. "what's the weather" returning appointments, or a symptom
being logged with the wrong text).
"""
from __future__ import annotations

from agent import Agent, new_state
from clinic.responses import say
from clinic.storage import load_store


def test_symptom_logged_with_the_right_text():
    agent = Agent(offline=True)
    state = new_state("p1")

    agent.run_turn(state, "hello")
    agent.run_turn(state, "I have a fever")   # asks for severity
    result = agent.run_turn(state, "4")       # completes the log

    symptoms = load_store()["symptoms"]
    assert symptoms[-1]["symptom"] == "I have a fever"
    assert symptoms[-1]["severity"] == 4
    assert "log_symptom" in result.tools_used


def test_unrelated_message_is_not_contaminated_by_history():
    agent = Agent(offline=True)
    state = new_state("p1")

    agent.run_turn(state, "book dermatology on 2026-11-05")
    agent.run_turn(state, "my appointments")
    result = agent.run_turn(state, "what's the weather like today")

    assert result.tool_calls == 0
    assert result.reply == say("fallback", "en")


def test_second_symptom_does_not_reuse_first_severity():
    agent = Agent(offline=True)
    state = new_state("p1")

    agent.run_turn(state, "I have a fever")
    agent.run_turn(state, "4")
    # New symptom, no severity yet -> must ask, not silently reuse "4".
    result = agent.run_turn(state, "I have a sore throat")

    assert result.tool_calls == 0
    assert result.reply == say("ask_severity", "en")
