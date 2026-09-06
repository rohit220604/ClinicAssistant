"""URL configuration for assistant_ui app."""
from django.urls import path

from . import views

app_name = "assistant_ui"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("chat/", views.chat, name="chat"),
]