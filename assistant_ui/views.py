"""Views for the assistant UI."""
from __future__ import annotations

import logging

from django.contrib import messages
from django.shortcuts import render

from . import forms, services
from .services import SESSION_CHAT_LOG, SESSION_CONVERSATION, SESSION_PATIENT_ID

logger = logging.getLogger(__name__)

DEFAULT_PATIENT_ID = "P001"


def _patient_id(request) -> str:
    stored = (request.session.get(SESSION_PATIENT_ID) or "").strip()
    return stored or DEFAULT_PATIENT_ID


def _set_patient(request, patient_id: str) -> None:
    previous = _patient_id(request)
    request.session[SESSION_PATIENT_ID] = patient_id
    if previous != patient_id:
        request.session.pop(SESSION_CONVERSATION, None)
        request.session.pop(SESSION_CHAT_LOG, None)


def dashboard(request):
    """Render the main dashboard page."""
    patient_id = _patient_id(request)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "set_patient":
            form = forms.PatientIdForm(request.POST)
            if form.is_valid():
                patient_id = form.cleaned_data["patient_id"].strip()
                _set_patient(request, patient_id)
                messages.success(request, f"Patient set to {patient_id}.")
            else:
                messages.error(request, "Please enter a valid patient ID.")

        elif action == "log_symptom":
            form = forms.SymptomForm(request.POST)
            if form.is_valid():
                try:
                    record = services.log_symptom(
                        patient_id=patient_id,
                        symptom=form.cleaned_data["symptom"],
                        severity=form.cleaned_data["severity"],
                    )
                    messages.success(
                        request,
                        f"Symptom logged ({record['id']}): "
                        f"{record['symptom']} at severity {record['severity']}.",
                    )
                except ValueError as exc:
                    logger.warning("log_symptom rejected: %s", exc)
                    messages.error(request, str(exc))
                except Exception:
                    logger.exception("log_symptom failed")
                    messages.error(
                        request,
                        "Could not log the symptom. Please try again.",
                    )
            else:
                messages.error(request, "Please correct the errors below.")

        elif action == "book_appointment":
            form = forms.AppointmentForm(request.POST)
            if form.is_valid():
                try:
                    record = services.book_appointment(
                        patient_id=patient_id,
                        department=form.cleaned_data["department"],
                        date=form.cleaned_data["date"].isoformat(),
                    )
                    if record.get("duplicate"):
                        messages.success(
                            request,
                            "This appointment was already booked "
                            f"({record['id']}): {record['department']} "
                            f"on {record['date']}.",
                        )
                    else:
                        messages.success(
                            request,
                            f"Appointment booked ({record['id']}): "
                            f"{record['department']} on {record['date']}.",
                        )
                except ValueError as exc:
                    logger.warning("book_appointment rejected: %s", exc)
                    messages.error(request, str(exc))
                except Exception:
                    logger.exception("book_appointment failed")
                    messages.error(
                        request,
                        "Could not book the appointment. Please try again.",
                    )
            else:
                messages.error(request, "Please correct the errors below.")

    appointments: list[dict] = []
    try:
        appointments = services.list_appointments(patient_id)
    except ValueError as exc:
        logger.warning("list_appointments rejected: %s", exc)
        messages.error(request, str(exc))
    except Exception:
        logger.exception("list_appointments failed")
        messages.error(
            request,
            "Could not load appointments. Please try again.",
        )

    context = {
        "patient_id": patient_id,
        "patient_form": forms.PatientIdForm(initial={"patient_id": patient_id}),
        "symptom_form": forms.SymptomForm(),
        "appointment_form": forms.AppointmentForm(),
        "appointments": appointments,
    }
    return render(request, "assistant_ui/dashboard.html", context)


def chat(request):
    """Handle chat messages via POST and return the updated page."""
    patient_id = _patient_id(request)

    if request.method == "POST":
        posted_patient = (request.POST.get("patient_id") or "").strip()
        if posted_patient:
            _set_patient(request, posted_patient)
            patient_id = posted_patient

        user_message = request.POST.get("message", "").strip()
        if not user_message:
            messages.error(request, "Please enter a message.")
        else:
            state = services.load_conversation(
                request.session.get(SESSION_CONVERSATION),
                patient_id,
            )
            try:
                reply = services.chat(user_message, state)
                request.session[SESSION_CONVERSATION] = (
                    services.serialize_conversation(state)
                )
                # Blocked safety turns do not write ConversationState.history;
                # keep a UI transcript so the real reply still appears.
                chat_log = list(request.session.get(SESSION_CHAT_LOG) or [])
                chat_log.append({"role": "user", "content": user_message})
                if (reply or "").strip():
                    chat_log.append({"role": "assistant", "content": reply})
                else:
                    messages.error(
                        request,
                        "The assistant returned an empty response.",
                    )
                request.session[SESSION_CHAT_LOG] = chat_log
            except Exception:
                logger.exception("Agent.run_turn failed")
                messages.error(
                    request,
                    "The assistant could not process that message. Please try again.",
                )

    context = {
        "patient_id": patient_id,
        "chat_history": list(request.session.get(SESSION_CHAT_LOG) or []),
    }
    return render(request, "assistant_ui/chat.html", context)
