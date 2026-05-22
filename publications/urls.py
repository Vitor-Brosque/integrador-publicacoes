from django.urls import path

from publications.views import publication_list


app_name = "publications"

urlpatterns = [
    path("", publication_list, name="publication_list"),
]
