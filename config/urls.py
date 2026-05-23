from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("", include("core.urls")),
    path("vehicles/", include("vehicles.urls")),
    path("publications/", include("publications.urls")),
    path("integrations/", include("social_accounts.urls")),
    path("admin/", admin.site.urls),
    path("posts/", include("posts.urls")),
]
