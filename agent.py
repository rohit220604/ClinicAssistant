"""Part 1 - the agent loop, written from scratch (no LangChain/LangGraph here).

Flow of one turn:
  1. Detect the language of the incoming message.
  2. Run the safety gate FIRST. EMERGENCY / MEDICAL_ADVICE / classifier-failure
     all short-circuit with a canned reply and run zero tools.
  3. Only if the verdict is SAFE do we enter the model loop: pass the tool
     schemas, let the model either ask for a missing slot or emit a tool call,
     execute the tool, feed the result back, and let the model reply.

Three failure paths are handled where tools are executed (see _run_tool):
unknown tool, tool raises, malformed arguments. A hard cap bounds tool calls per
turn so a misbehaving model can't loop forever.

The three contract functions are re-exported so graders can also do
`from agent import log_symptom, book_appointment, list_appointments`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date

from clinic.config import settings
from clinic.intents import Verdict
from clinic.language import detect_language
from clinic.llm import get_client
from clinic.metrics import log_llm_call, log_turn, stopwatch
from clinic.prompts import build_system_prompt
from clinic.registry import UnknownToolError, execute_tool
from clinic.responses import say
from clinic.safety import classify_safety
from clinic.schemas import TOOL_SCHEMAS
from clinic.state import ConversationState
from clinic.tools import book_appointment, list_appointments, log_symptom  # noqa: F401 (re-export)

# Which canned reply to send for each blocking verdict.
_BLOCK_REPLY = {Verdict.EMERGENCY: "emergency", Verdict.MEDICAL_ADVICE: "medical_advice"}


@dataclass
class TurnResult:
    reply: str
    verdict: str
    source: str
    blocked: bool
    degraded: bool
    tool_calls: int
    llm_calls: int
    turn_ms: float
    tools_used: list[str] = field(default_factory=list)


class Agent:
    def __init__(self, client=None, offline: bool = False, max_tool_calls: int | None = None):
        self.client = client or get_client(offline)
        self.offline = offline or getattr(self.client, "chat_model", "") == "offline-keyword"
        self.max_tool_calls = max_tool_calls or settings.max_tool_calls

    def run_turn(self, state: ConversationState, message: str) -> TurnResult:
        with stopwatch() as elapsed:
            lang, safety, llm_calls = self._safety_step(message)
            state.language = lang

            # Anything not clearly SAFE stops here - no routing, no tools.
            if safety.degraded or safety.verdict != Verdict.SAFE:
                reply = self.block_reply(safety.verdict, safety.degraded, lang)
                log_turn(elapsed(), llm_calls, self.offline)
                return TurnResult(reply, safety.verdict, safety.source, True,
                                  safety.degraded, 0, llm_calls, elapsed())

            reply, tool_calls, tools_used, chat_llm_calls = self._model_loop(state, message, lang)
            llm_calls += chat_llm_calls

            log_turn(elapsed(), llm_calls, self.offline)
            return TurnResult(reply, safety.verdict, safety.source, False, False,
                              tool_calls, llm_calls, elapsed(), tools_used)

    # --- steps (shared by run_turn and the LangGraph router) -------------
    def _safety_step(self, message: str):
        """Language detection + the safety gate. Returns (language, SafetyResult,
        classifier llm-call count). Shared so the graph can't drift from the loop."""
        lang = detect_language(message)
        safety = classify_safety(message, self.client)
        llm_calls = 0
        if safety.source in ("llm", "fail_closed"):
            llm_calls = 1
            log_llm_call(safety.latency_ms, self.client.classifier_model, "safety")
        return lang, safety, llm_calls

    def block_reply(self, verdict: str, degraded: bool, lang: str) -> str:
        if degraded:
            return say("safety_degraded", lang)
        return say(_BLOCK_REPLY[verdict], lang)

    # --- internals -------------------------------------------------------
    def _model_loop(self, state: ConversationState, message: str, lang: str):
        state.add_user(message)
        system = {"role": "system", "content": build_system_prompt(state.patient_id, date.today().isoformat(), lang)}

        tool_calls_made = 0
        llm_calls = 0
        tools_used: list[str] = []
        reply: str | None = None
        # +2 gives the model room to read tool results and reply after the cap.
        for _ in range(self.max_tool_calls + 2):
            result = self.client.chat(
                [system] + state.history,
                TOOL_SCHEMAS,
                state=state,
            )
            llm_calls += 1
            log_llm_call(result.llm_ms, self.client.chat_model, "chat")

            if not result.tool_calls:
                state.add_assistant(result.assistant_message)
                reply = result.text or ""
                break

            if tool_calls_made + len(result.tool_calls) > self.max_tool_calls:
                reply = say("tool_cap", lang)
                state.add_assistant({"role": "assistant", "content": reply})
                break

            state.add_assistant(result.assistant_message)
            for call in result.tool_calls:
                tool_calls_made += 1
                tools_used.append(call.name)
                state.add_tool_result(call.id, self._run_tool(call, state.patient_id))

        if reply is None:
            reply = say("tool_cap", lang)
            state.add_assistant({"role": "assistant", "content": reply})
        return reply, tool_calls_made, tools_used, llm_calls

    def _run_tool(self, call, patient_id: str) -> str:
        # Failure path 1: malformed arguments (not valid JSON / not an object).
        try:
            args = json.loads(call.raw_arguments or "{}")
        except (ValueError, TypeError):
            return json.dumps({"error": f"malformed arguments: {call.raw_arguments!r}"})
        if not isinstance(args, dict):
            return json.dumps({"error": "arguments must be a JSON object"})
        try:
            result = execute_tool(call.name, args, patient_id)
            return json.dumps(result, ensure_ascii=False, default=str)
        except UnknownToolError:
            # Failure path 2: the model called a tool that doesn't exist.
            return json.dumps({"error": f"unknown tool '{call.name}'"})
        except (ValueError, TypeError) as exc:
            # Failure path 3: the tool raised (bad severity, missing/extra args...).
            return json.dumps({"error": str(exc)})


def new_state(patient_id: str) -> ConversationState:
    return ConversationState(patient_id=patient_id)
