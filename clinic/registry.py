"""Name -> function mapping and the executor the loop calls.

`patient_id` is deliberately injected here from conversation state, not taken
from the model. The model can never set which patient it is acting for - that
removes a whole class of "invented argument" bugs.
"""
from __future__ import annotations

from typing import Any

from clinic.tools import book_appointment, list_appointments, log_symptom

TOOL_REGISTRY = {
    "log_symptom": log_symptom,
    "book_appointment": book_appointment,
    "list_appointments": list_appointments,
}


class UnknownToolError(Exception):
    """The model asked for a tool that isn't registered."""


def execute_tool(name: str, arguments: dict[str, Any], patient_id: str):
    if name not in TOOL_REGISTRY:
        raise UnknownToolError(name)
    fn = TOOL_REGISTRY[name]
    # Wrong or extra keys raise TypeError -> the loop's malformed-args path.
    return fn(patient_id=patient_id, **arguments)
