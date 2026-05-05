from django.urls import path

from posts.views import create_post

from posts.views import create_post, create_post_from_vehicle

app_name = "posts"

urlpatterns = [
    path("create/", create_post, name="create_post"),
    path("create-from-vehicle/", create_post_from_vehicle, name="create_post_from_vehicle"),
    ]
