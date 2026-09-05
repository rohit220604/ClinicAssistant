"""Deterministic keyword matching.

This module does three jobs with one set of phrase tables:
  1. the offline classifier (so the eval runs with no API key),
  2. a fast pre-router that short-circuits obvious messages before we spend an
     LLM call (the Part 5 optimisation),
  3. a safety net the LLM classifier is checked against for clear emergencies.

Phrases cover English, Hindi (Devanagari) and Hinglish (romanised Hindi). The
lists are intentionally small and readable - add a phrase, not a regex.
"""
from __future__ import annotations

import re

from clinic.intents import Intent, Verdict

_DEVANAGARI = re.compile(r"[\u0900-\u097F]")

EMERGENCY = [
    # English
    "chest pain", "pain in my chest", "tight chest", "can't breathe",
    "cant breathe", "cannot breathe", "not breathing", "trouble breathing",
    "difficulty breathing", "short of breath", "heart attack", "stroke",
    "unconscious", "passed out", "fainted", "collapsed", "seizure", "choking",
    "bleeding heavily", "heavy bleeding", "won't stop bleeding", "severe bleeding",
    "overdose", "suicide", "kill myself", "want to die", "end my life",
    "ending my life", "harm myself", "hurt myself", "no pulse", "blue lips",
    # Devanagari
    "सीने में दर्द", "साँस नहीं", "सांस नहीं", "साँस लेने में", "सांस लेने में",
    "बेहोश", "दिल का दौरा", "खून बह", "आत्महत्या", "जान दे",
    # Hinglish
    "seene mein dard", "seene me dard", "chest me dard", "saans nahi", "saas nahi",
    "saans lene", "behosh", "dil ka daura", "khoon beh", "aatmhatya", "jaan de",
    "mar jaunga", "marne wala", "daura pad",
]

MEDICAL_ADVICE = [
    # English
    "should i take", "which medicine", "what medicine", "what medication",
    "which medication", "prescribe", "prescription", "is it serious",
    "what disease", "diagnos", "what's wrong with me", "whats wrong with me",
    "should i be worried", "dosage", "how much medicine", "can i take",
    "is it cancer", "is it covid", "do i have covid", "do i have corona",
    "do i have cancer", "what should i do about",
    # Devanagari
    "कौन सी दवा", "कौनसी दवा", "क्या दवा", "दवा बताओ", "दवा लूँ", "मुझे क्या हुआ",
    "कौन सी बीमारी", "क्या बीमारी", "क्या यह गंभीर",
    # Hinglish
    "konsi dawa", "kaunsi dawa", "kaun si dawa", "kya dawa", "dawa batao",
    "dawa bata", "dawa loon", "mujhe kya hua", "kya bimari", "konsi bimari",
    "kya yeh serious", "kya lena chahiye", "kya khaun",
]

LIST_APPOINTMENTS = [
    "my appointment", "my appointments", "upcoming appointment", "list appointment",
    "show my appointment", "when is my appointment", "any appointment",
    "check my appointment", "what appointments", "dikhao", "dikha do",
    "मेरी अपॉइंटमेंट", "अपॉइंटमेंट कब", "कब है मेरी", "अपॉइंटमेंट देख",
    "meri appointment", "appointment kab", "kab hai meri", "appointment dekh",
    "appointment check",
]

BOOK_APPOINTMENT = [
    "book", "appointment", "schedule", "make an appointment", "see a doctor",
    "consult", "want to visit",
    "अपॉइंटमेंट", "बुक", "मिलना चाहता", "दिखाना है",
    "book kar", "book karni", "book karna", "appointment chahiye", "milna chahta",
    "dikhana hai",
]

LOG_SYMPTOM = [
    "i have", "i've got", "i am having", "feeling", "fever", "headache",
    "head ache", "cough", "cold", "sore throat", "stomach", "pain in", "hurts",
    "ache", "nausea", "vomit", "dizzy", "rash", "runny nose", "log my symptom",
    "बुखार", "सिरदर्द", "सिर दर्द", "खांसी", "खाँसी", "सर्दी", "दर्द", "पेट",
    "गले", "जुकाम", "उल्टी", "चक्कर",
    "bukhar", "bukhaar", "sardi", "khansi", "khaansi", "jukam", "zukam", "dard",
    "sar dard", "sir dard", "pet dard", "gale mein", "ulti", "chakkar",
    "tabiyat kharab",
]

SMALL_TALK = [
    "hello", "hey", "thanks", "thank you", "good morning", "good evening",
    "how are you", "who are you", "what can you do", "goodbye",
    "नमस्ते", "धन्यवाद", "शुक्रिया", "आप कौन", "कैसे हो",
    "namaste", "namaskar", "shukriya", "dhanyavaad", "aap kaun", "kaise ho",
]

# Very short greetings need whole-word matching so "hi" doesn't fire inside
# "this" or "chai".
SMALL_TALK_WORDS = {"hi", "ok", "okay", "bye", "yo", "hii", "helo"}


def _contains(text: str, phrase: str) -> bool:
    if _DEVANAGARI.search(phrase):
        return phrase in text
    # Left word boundary + an optional common suffix, so "appointment" also
    # matches "appointments" and "diagnos" matches "diagnose/diagnosed" without
    # firing inside unrelated words like "enter".
    return re.search(rf"\b{re.escape(phrase)}(e|s|es|ed|ing)?\b", text) is not None


def _any(text: str, phrases: list[str]) -> bool:
    return any(_contains(text, p) for p in phrases)


def keyword_safety(message: str) -> str | None:
    """EMERGENCY / MEDICAL_ADVICE when confident, else None (defer to the LLM)."""
    text = message.lower()
    if _any(text, EMERGENCY):
        return Verdict.EMERGENCY
    if _any(text, MEDICAL_ADVICE):
        return Verdict.MEDICAL_ADVICE
    return None


def keyword_intent(message: str) -> str | None:
    """Best-guess intent from keywords, or None if nothing matches.

    Order matters: safety-critical labels first, then the explicit actions
    (list before book, since "my appointments" also contains "appointment"),
    then symptoms, then small talk.
    """
    text = message.lower()
    if _any(text, EMERGENCY):
        return Intent.EMERGENCY
    if _any(text, MEDICAL_ADVICE):
        return Intent.MEDICAL_ADVICE
    if _any(text, LIST_APPOINTMENTS):
        return Intent.LIST_APPOINTMENTS
    if _any(text, BOOK_APPOINTMENT):
        return Intent.BOOK_APPOINTMENT
    if _any(text, LOG_SYMPTOM):
        return Intent.LOG_SYMPTOM
    tokens = set(re.findall(r"[a-z]+", text))
    if _any(text, SMALL_TALK) or tokens & SMALL_TALK_WORDS:
        return Intent.SMALL_TALK
    return None
