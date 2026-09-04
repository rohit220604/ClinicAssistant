"""Tool schemas handed to the model.

Groq uses the OpenAI function-calling shape. The names here must match the keys
in TOOL_REGISTRY (clinic/registry.py) exactly - that mapping is how a parsed
tool call becomes a real function call.
"""
from __future__ import annotations

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "log_symptom",
            "description": "Record a symptom the patient reports, with a severity from 1 (mild) to 5 (severe).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptom": {
                        "type": "string",
                        "description": "Short description of the symptom, e.g. 'headache'.",
                    },
                    "severity": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "How severe it is, 1-5. Ask the patient if unknown.",
                    },
                },
                "required": ["symptom", "severity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment for the patient in a department on a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Clinic department, e.g. 'cardiology'.",
                    },
                    "date": {
                        "type": "string",
                        "description": "ISO date (YYYY-MM-DD). Ask the patient if not given; never invent it.",
                    },
                },
                "required": ["department", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_appointments",
            "description": "List the patient's booked appointments.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
