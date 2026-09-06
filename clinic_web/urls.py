"""URL configuration for clinic_web project."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("", include("assistant_ui.urls")),
]