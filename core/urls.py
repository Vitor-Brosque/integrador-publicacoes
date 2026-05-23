from django.urls import path

from core.views import home, system_check


app_name = "core"

urlpatterns = [
    path("", home, name="home"),
    path("system-check/", system_check, name="system_check"),
]
