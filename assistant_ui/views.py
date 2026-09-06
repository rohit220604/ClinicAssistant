"""Views for the assistant UI."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import render

from . import forms, services


def dashboard(request):
    """Render the main dashboard page."""
    patient_id = "P001"

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "set_patient":
            patient_id = request.POST.get("patient_id", "P001")
        elif action == "log_symptom":
            form = forms.SymptomForm(request.POST)
            if form.is_valid():
                services.log_symptom(
                    patient_id=request.POST.get("patient_id", "P001"),
                    symptom=form.cleaned_data["symptom"],
                    severity=form.cleaned_data["severity"],
                )
                messages.success(request, "Symptom logged successfully (demo).")
            else:
                messages.error(request, "Please correct the errors below.")
        elif action == "book_appointment":
            form = forms.AppointmentForm(request.POST)
            if form.is_valid():
                services.book_appointment(
                    patient_id=request.POST.get("patient_id", "P001"),
                    department=form.cleaned_data["department"],
                    date_str=form.cleaned_data["date"].isoformat(),
                )
                messages.success(request, "Appointment booked successfully (demo).")
            else:
                messages.error(request, "Please correct the errors below.")

    context = {
        "patient_id": patient_id,
        "patient_form": forms.PatientIdForm(initial={"patient_id": patient_id}),
        "symptom_form": forms.SymptomForm(),
        "appointment_form": forms.AppointmentForm(),
        "appointments": services.list_appointments(patient_id),
        "messages": messages.get_messages(request),
    }
    return render(request, "assistant_ui/dashboard.html", context)


def chat(request):
    """Handle chat messages via POST and return the updated page."""
    if request.method != "POST":
        return render(request, "assistant_ui/chat.html", {"patient_id": "P001"})

    patient_id = request.POST.get("patient_id", "P001")
    user_message = request.POST.get("message", "").strip()

    if not user_message:
        messages.error(request, "Please enter a message.")
    else:
        assistant_message = services.chat(user_message, patient_id)
        messages.success(request, assistant_message)

    context = {
        "patient_id": patient_id,
        "user_message": user_message,
        "messages": messages.get_messages(request),
    }
    return render(request, "assistant_ui/chat.html", context)