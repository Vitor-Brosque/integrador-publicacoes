from django.urls import path

from .views import integrations_dashboard, platform_integration


app_name = "social_accounts"

urlpatterns = [
    path("", integrations_dashboard, name="integrations_dashboard"),
    path("<slug:platform_slug>/", platform_integration, name="platform_integration"),
]
