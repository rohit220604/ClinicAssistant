"""Part 3 - the safety gate's failure paths (the tests the assignment says to
never cut).

When the classifier itself fails - it raises, or it hangs past the timeout - the
agent must fail CLOSED: block the message, show the degraded/safe guidance, and
run no tools. We prove both here by feeding the agent fake clients whose `chat`
raises if it is ever called (so "a tool ran" would blow up the test).
"""
from __future__ import annotations

import time
from dataclasses import replace

import clinic.safety as safety
from agent import Agent, new_state
from clinic.config import settings
from clinic.responses import say
from clinic.tools import list_appointments

# A message with no emergency/medical keywords, so the keyword fast-path can't
# resolve it and we are forced onto the (failing) classifier.
NEUTRAL = "please help me figure out my thing"


class RaisingClient:
    classifier_model = "fake"
    chat_model = "fake"

    def classify(self, message, kind, timeout=None):
        raise RuntimeError("classifier exploded")

    def chat(self, *args, **kwargs):
        raise AssertionError("a tool/model call ran during a blocked turn")


class SleepingClient:
    classifier_model = "fake"
    chat_model = "fake"

    def classify(self, message, kind, timeout=None):
        time.sleep(1.0)
        return "SAFE"

    def chat(self, *args, **kwargs):
        raise AssertionError("a tool/model call ran during a blocked turn")


def test_classifier_raises_fails_closed():
    agent = Agent(client=RaisingClient())
    state = new_state("p1")

    result = agent.run_turn(state, NEUTRAL)

    assert result.blocked is True
    assert result.degraded is True
    assert result.source == "fail_closed"
    assert result.reply == say("safety_degraded", "en")
    # No tool ran.
    assert result.tool_calls == 0
    assert list_appointments("p1") == []


def test_classifier_times_out_fails_closed(monkeypatch):
    # Shrink the classifier timeout so the 1s sleep trips it fast.
    monkeypatch.setattr(safety, "settings", replace(settings, classifier_timeout=0.2))
    agent = Agent(client=SleepingClient())
    state = new_state("p2")

    started = time.perf_counter()
    result = agent.run_turn(state, NEUTRAL)
    elapsed = time.perf_counter() - started

    assert result.degraded is True
    assert result.source == "fail_closed"
    assert result.reply == say("safety_degraded", "en")
    assert result.tool_calls == 0
    assert list_appointments("p2") == []
    # We gave up near the timeout, not after the full 1s sleep.
    assert elapsed < 0.8


def test_failure_is_countable(monkeypatch, tmp_path):
    log = tmp_path / "safety.jsonl"
    monkeypatch.setattr(safety, "SAFETY_LOG", log)
    client = RaisingClient()

    safety.classify_safety(NEUTRAL, client)
    safety.classify_safety(NEUTRAL, client)

    assert safety.failure_count(log) == 2
