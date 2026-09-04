"""Clinic Assistant package.

The three functions the assignment fixes as a contract are re-exported here so
graders can do `from clinic import log_symptom, book_appointment, list_appointments`.
"""
from clinic.tools import book_appointment, list_appointments, log_symptom

__all__ = ["log_symptom", "book_appointment", "list_appointments"]
