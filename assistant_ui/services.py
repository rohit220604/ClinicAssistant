"""Django service layer that delegates to the existing clinic backend.

Direct actions call clinic.tools. Chat uses Agent.run_turn() with a
ConversationState that the views persist in the Django session.
"""
from __future__ import annotations

from agent import Agent, new_state
from clinic.state import ConversationState
from clinic.tools import book_appointment, list_appointments, log_symptom

SESSION_PATIENT_ID = "patient_id"
SESSION_CONVERSATION = "conversation_state"
SESSION_CHAT_LOG = "chat_log"


def serialize_conversation(state: ConversationState) -> dict:
    """Plain dict of ConversationState fields for session JSON storage."""
    return {
        "patient_id": state.patient_id,
        "language": state.language,
        "history": state.history,
        "pending_intent": state.pending_intent,
        "pending_department": state.pending_department,
        "pending_date": state.pending_date,
        "pending_symptom": state.pending_symptom,
    }


def load_conversation(data: dict | None, patient_id: str) -> ConversationState:
    """Rebuild ConversationState, or start a new one if patient does not match."""
    if not data or data.get("patient_id") != patient_id:
        return new_state(patient_id)
    return ConversationState(
        patient_id=patient_id,
        language=data.get("language") or "en",
        history=list(data.get("history") or []),
        pending_intent=data.get("pending_intent"),
        pending_department=data.get("pending_department"),
        pending_date=data.get("pending_date"),
        pending_symptom=data.get("pending_symptom"),
    )


def chat(message: str, state: ConversationState) -> str:
    """One agent turn. Mutates `state` in place (history and pending slots)."""
    result = Agent().run_turn(state, message)
    return result.reply
