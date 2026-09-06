"""Provider clients.

Two implementations behind one small interface:
  - GroqClient  : the real thing (chat + tool calling + classification).
  - OfflineClient: a deterministic stub built on the keyword rules, so the eval
    and the CLI run with no API key. This is the `--offline` model.

Both return the same normalised shapes (ChatResult / RawToolCall) so the agent
loop never has to care which one it is talking to.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field

from clinic import slots
from clinic.config import settings
from clinic.intents import INTENTS, VERDICTS, Intent, Verdict
from clinic.language import detect_language
from clinic.responses import say
from clinic.rules import keyword_intent, keyword_safety

_SAFETY_PROMPT = (
    "You are a safety classifier for a clinic assistant. Read the patient's "
    "message and reply with exactly one word:\n"
    "EMERGENCY - a life-threatening or urgent crisis needing immediate care "
    "(chest pain, can't breathe, severe bleeding, unconscious, stroke signs, "
    "suicidal thoughts, overdose, etc.).\n"
    "MEDICAL_ADVICE - asking for a diagnosis, a medicine, a dose, or 'what's "
    "wrong with me' / 'is it serious'.\n"
    "SAFE - everything else, including reporting a symptom to log, booking, "
    "listing appointments, and small talk.\n"
    "Reply with only the label."
)

_INTENT_PROMPT = (
    "Classify the patient's message into exactly one label from:\n"
    "LOG_SYMPTOM, BOOK_APPOINTMENT, LIST_APPOINTMENTS, EMERGENCY, "
    "MEDICAL_ADVICE, SMALL_TALK, UNKNOWN.\n"
    "If the message both reports a symptom and asks for an action (book or "
    "list), choose the action. Reply with only the label."
)

_PROMPTS = {"safety": _SAFETY_PROMPT, "intent": _INTENT_PROMPT}
_VALID = {"safety": set(VERDICTS), "intent": set(INTENTS)}


@dataclass
class RawToolCall:
    id: str
    name: str
    raw_arguments: str


@dataclass
class ChatResult:
    assistant_message: dict
    tool_calls: list[RawToolCall] = field(default_factory=list)
    text: str | None = None
    llm_ms: float = 0.0


def _normalise_label(raw: str, kind: str) -> str:
    token = (raw or "").strip().upper().split()[0] if raw and raw.strip() else ""
    token = token.strip(".:,")
    if token in _VALID[kind]:
        return token
    return Verdict.SAFE if kind == "safety" else Intent.UNKNOWN


class GroqClient:
    def __init__(self, chat_model: str | None = None, classifier_model: str | None = None):
        from groq import Groq  # imported lazily so offline runs never need it

        self._client = Groq(api_key=settings.api_key)
        self.chat_model = chat_model or settings.chat_model
        self.classifier_model = classifier_model or settings.classifier_model

    def classify(self, message: str, kind: str, timeout: float | None = None) -> str:
        resp = self._client.chat.completions.create(
            model=self.classifier_model,
            messages=[
                {"role": "system", "content": _PROMPTS[kind]},
                {"role": "user", "content": message},
            ],
            temperature=0,
            max_tokens=4,
            timeout=timeout,
        )
        return _normalise_label(resp.choices[0].message.content, kind)

    def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        timeout: float | None = None,
        state=None,
    ) -> ChatResult:
        t0 = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0,
            timeout=timeout,
        )
        llm_ms = (time.perf_counter() - t0) * 1000
        msg = resp.choices[0].message
        raw_calls = [
            RawToolCall(tc.id, tc.function.name, tc.function.arguments)
            for tc in (msg.tool_calls or [])
        ]
        return ChatResult(msg.model_dump(exclude_none=True), raw_calls, msg.content, llm_ms)


class OfflineClient:
    """Rule-based stand-in. Deterministic and key-free."""

    classifier_model = "offline-keyword"
    chat_model = "offline-keyword"

    def classify(self, message: str, kind: str, timeout: float | None = None) -> str:
        if kind == "safety":
            return keyword_safety(message) or Verdict.SAFE
        return keyword_intent(message) or Intent.UNKNOWN

    def chat(
        self,
        messages: list[dict],
        tools: list[dict],
        timeout: float | None = None,
        state=None,
    ) -> ChatResult:
        t0 = time.perf_counter()
        result = self._decide(messages, state)
        result.llm_ms = (time.perf_counter() - t0) * 1000
        return result

    # --- internals -------------------------------------------------------
    def _decide(self, messages: list[dict], state=None) -> ChatResult:
        if messages and messages[-1]["role"] == "tool":
            text = self._confirm(messages[-1]["content"])
            return ChatResult(
                {"role": "assistant", "content": text},
                text=text,
            )

        user_msgs = [
            m["content"]
            for m in messages
            if m["role"] == "user" and m.get("content")
        ]

        latest = user_msgs[-1] if user_msgs else ""
        lang = detect_language(latest)

        intent = keyword_intent(latest) or Intent.UNKNOWN

        if state and state.pending_intent == Intent.BOOK_APPOINTMENT:
            if intent in {
                Intent.LIST_APPOINTMENTS,
                Intent.LOG_SYMPTOM,
                Intent.SMALL_TALK,
                Intent.UNKNOWN,
            }:
                return self._continue_booking(state, latest, lang)

            if intent == Intent.BOOK_APPOINTMENT:
                return self._continue_booking(state, latest, lang)

            state.pending_intent = None
            state.pending_department = None
            state.pending_date = None

        if state and state.pending_intent == Intent.LOG_SYMPTOM:
            if intent in {Intent.UNKNOWN, Intent.LOG_SYMPTOM}:
                return self._continue_logging(state, latest, lang)

            state.pending_intent = None
            state.pending_symptom = None

        if intent == Intent.BOOK_APPOINTMENT:
            return self._start_booking(state, latest, lang)

        if intent == Intent.LOG_SYMPTOM:
            return self._start_logging(state, latest, lang)

        if intent == Intent.LIST_APPOINTMENTS:
            return self._call("list_appointments", {})

        return self._text(say("fallback", lang))
    
    def _start_booking(self, state, text, lang):
        dept = slots.find_department(text)
        appointment_date = slots.find_date(text)

        if dept and appointment_date:
            state.pending_intent = None
            return self._call(
                "book_appointment",
                {
                    "department": dept,
                    "date": appointment_date,
                },
            )

        state.pending_intent = Intent.BOOK_APPOINTMENT
        state.pending_department = dept
        state.pending_date = appointment_date

        if not dept:
            return self._text(say("ask_department", lang))

        return self._text(say("ask_date", lang))
    
    def _continue_booking(self, state, text, lang):
        dept = state.pending_department or slots.find_department(text)
        appointment_date = state.pending_date or slots.find_date(text)

        if not dept:
            dept = slots.find_department(text)

        if not appointment_date:
            appointment_date = slots.find_date(text)

        state.pending_department = dept
        state.pending_date = appointment_date

        if not dept:
            return self._text(say("ask_department", lang))

        if not appointment_date:
            return self._text(say("ask_date", lang))

        state.pending_intent = None
        state.pending_department = None
        state.pending_date = None

        return self._call(
            "book_appointment",
            {
                "department": dept,
                "date": appointment_date,
            },
        )
    
    def _start_logging(self, state, text, lang):
        severity = slots.find_severity(text)

        state.pending_intent = Intent.LOG_SYMPTOM
        state.pending_symptom = text

        if severity is None:
            return self._text(say("ask_severity", lang))

        state.pending_intent = None
        state.pending_symptom = None

        return self._call(
            "log_symptom",
            {
                "symptom": text,
                "severity": severity,
            },
        )

    def _continue_logging(self, state, text, lang):
        severity = slots.find_severity(text)

        if severity is None:
            return self._text(say("ask_severity", lang))

        symptom = state.pending_symptom

        state.pending_intent = None
        state.pending_symptom = None

        return self._call(
            "log_symptom",
            {
                "symptom": symptom,
                "severity": severity,
            },
        )

    def _book(self, text: str, lang: str) -> ChatResult:
        dept = slots.find_department(text)
        date = slots.find_date(text)
        if dept and date:
            return self._call("book_appointment", {"department": dept, "date": date})
        if not dept:
            return self._text(say("ask_department", lang))
        return self._text(say("ask_date", lang))

    def _log(self, user_msgs: list[str], text: str, lang: str) -> ChatResult:
        severity = slots.find_severity(text)
        symptom = user_msgs[0] if user_msgs else text
        if severity is None:
            return self._text(say("ask_severity", lang))
        return self._call("log_symptom", {"symptom": symptom, "severity": severity})

    def _call(self, name: str, args: dict) -> ChatResult:
        call_id = f"call_{uuid.uuid4().hex[:8]}"
        assistant = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": call_id, "type": "function",
                 "function": {"name": name, "arguments": json.dumps(args)}}
            ],
        }
        return ChatResult(assistant, [RawToolCall(call_id, name, json.dumps(args))])

    def _text(self, text: str) -> ChatResult:
        return ChatResult({"role": "assistant", "content": text}, text=text)

    def _confirm(self, tool_content: str) -> str:
        try:
            data = json.loads(tool_content)
        except (TypeError, ValueError):
            return "Done."
        if isinstance(data, list):
            if not data:
                return "You have no appointments booked yet."
            lines = [f"- {a['department']} on {a['date']}" for a in data]
            return "Here are your appointments:\n" + "\n".join(lines)
        if "department" in data:
            return f"Booked: {data['department']} on {data['date']}."
        if "symptom" in data:
            return f"Logged your symptom '{data['symptom']}' at severity {data['severity']}."
        return "Done."


def get_client(offline: bool):
    if offline or not settings.has_key:
        return OfflineClient()
    return GroqClient()
