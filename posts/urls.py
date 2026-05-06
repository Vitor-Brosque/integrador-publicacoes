from django.urls import path

from posts.views import (
    approve_post,
    create_post,
    create_post_from_vehicle,
    publish_post,
    review_post,
    save_review_post,
)


app_name = "posts"

urlpatterns = [
    path("create/", create_post, name="create_post"),
    path("create-from-vehicle/", create_post_from_vehicle, name="create_post_from_vehicle"),
    path("<int:post_id>/review/", review_post, name="review_post"),
    path("<int:post_id>/approve/", approve_post, name="approve_post"),
    path("<int:post_id>/publish/", publish_post, name="publish_post"),
    path("<int:post_id>/save-review/", save_review_post, name="save_review_post"),
]
