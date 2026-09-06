"""Forms for the assistant UI."""
from django import forms


class PatientIdForm(forms.Form):
    patient_id = forms.CharField(
        label="Patient ID",
        max_length=50,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter patient ID (e.g., P001)",
                "value": "P001",
            }
        ),
    )


class SymptomForm(forms.Form):
    symptom = forms.CharField(
        label="Symptom",
        max_length=500,
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Describe your symptom...",
                "rows": 3,
            }
        ),
    )
    severity = forms.IntegerField(
        label="Severity (1-5)",
        min_value=1,
        max_value=5,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "value": 3,
            }
        ),
    )


class AppointmentForm(forms.Form):
    department = forms.CharField(
        label="Department",
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g., cardiology, dermatology",
            }
        ),
    )
    date = forms.DateField(
        label="Date",
        required=True,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )