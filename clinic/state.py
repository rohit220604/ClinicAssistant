"""Multi-turn conversation state.

Holds the things that must survive between messages: which patient we are
talking to, the language to reply in, and the running message history (which is
also "what has been collected so far" - a half-finished booking lives in these
messages). The system prompt is NOT stored here; it is rebuilt every turn so
patient_id and today's date are always current.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConversationState:
    patient_id: str
    language: str = "en"
    history: list[dict] = field(default_factory=list)

    def add_user(self, text: str) -> None:
        self.history.append({"role": "user", "content": text})

    def add_assistant(self, message: dict) -> None:
        self.history.append(message)

    def add_tool_result(self, call_id: str, content: str) -> None:
        self.history.append({"role": "tool", "tool_call_id": call_id, "content": content})
