from django.urls import path

from vehicles.views import (
    vehicle_add_media,
    vehicle_create,
    vehicle_delete_media,
    vehicle_detail,
    vehicle_edit,
    vehicle_list,
)


app_name = "vehicles"

urlpatterns = [
    path("", vehicle_list, name="vehicle_list"),
    path("create/", vehicle_create, name="vehicle_create"),
    path("<int:vehicle_id>/", vehicle_detail, name="vehicle_detail"),
    path("<int:vehicle_id>/edit/", vehicle_edit, name="vehicle_edit"),
    path("<int:vehicle_id>/media/add/", vehicle_add_media, name="vehicle_add_media"),
    path(
        "<int:vehicle_id>/media/<int:media_id>/delete/",
        vehicle_delete_media,
        name="vehicle_delete_media",
    ),
]
