"""Part 1 - the three tool failure paths and the tool-call cap."""
from __future__ import annotations

import json

from agent import Agent, new_state
from clinic.llm import ChatResult, RawToolCall
from clinic.responses import say


def _run(name, raw_args):
    agent = Agent(offline=True)
    return json.loads(agent._run_tool(RawToolCall("c1", name, raw_args), "p1"))


def test_unknown_tool_is_reported_not_raised():
    out = _run("frobnicate", "{}")
    assert "unknown tool" in out["error"]


def test_malformed_arguments_are_reported():
    out = _run("log_symptom", "{not valid json")
    assert "malformed" in out["error"]


def test_tool_that_raises_is_reported():
    out = _run("book_appointment", '{"department": "cardiology", "date": "someday"}')
    assert "error" in out and "ISO" in out["error"]


def test_extra_argument_is_reported():
    out = _run("log_symptom", '{"symptom": "x", "severity": 2, "bogus": 1}')
    assert "error" in out


class LoopingClient:
    """Always asks for another tool call, to exercise the per-turn cap."""

    classifier_model = "fake"
    chat_model = "fake"

    def classify(self, message, kind, timeout=None):
        return "SAFE"

    def chat(self, messages, tools, timeout=None, state=None):
        assistant = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "c", "type": "function",
                 "function": {"name": "list_appointments", "arguments": "{}"}}
            ],
        }
        return ChatResult(assistant, [RawToolCall("c", "list_appointments", "{}")])


def test_tool_call_cap_gives_graceful_answer():
    agent = Agent(client=LoopingClient(), max_tool_calls=2)
    result = agent.run_turn(new_state("p1"), "keep going please")

    assert result.tool_calls <= 2
    assert result.reply == say("tool_cap", "en")
