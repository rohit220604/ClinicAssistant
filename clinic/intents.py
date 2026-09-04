"""The exact label strings the assignment fixes.

Kept as module constants (not bare strings scattered around) so a typo becomes
an import error instead of a silent mislabel.
"""
from __future__ import annotations


class Intent:
    LOG_SYMPTOM = "LOG_SYMPTOM"
    BOOK_APPOINTMENT = "BOOK_APPOINTMENT"
    LIST_APPOINTMENTS = "LIST_APPOINTMENTS"
    EMERGENCY = "EMERGENCY"
    MEDICAL_ADVICE = "MEDICAL_ADVICE"
    SMALL_TALK = "SMALL_TALK"
    UNKNOWN = "UNKNOWN"


class Verdict:
    EMERGENCY = "EMERGENCY"
    MEDICAL_ADVICE = "MEDICAL_ADVICE"
    SAFE = "SAFE"


INTENTS = [
    Intent.LOG_SYMPTOM,
    Intent.BOOK_APPOINTMENT,
    Intent.LIST_APPOINTMENTS,
    Intent.EMERGENCY,
    Intent.MEDICAL_ADVICE,
    Intent.SMALL_TALK,
    Intent.UNKNOWN,
]

VERDICTS = [Verdict.EMERGENCY, Verdict.MEDICAL_ADVICE, Verdict.SAFE]
