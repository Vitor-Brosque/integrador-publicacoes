from django.urls import path

from posts.views import (
    approve_post,
    create_post,
    create_post_from_vehicle,
    pending_review_list,
    publish_post,
    publish_instagram_real,
    publish_all_real,
    post_list,
    real_publish_check,
    review_post,
    save_review_post,
)


app_name = "posts"

urlpatterns = [
    path("", post_list, name="post_list"),
    path("pending-review/", pending_review_list, name="pending_review_list"),
    path("create/", create_post, name="create_post"),
    path("create-from-vehicle/", create_post_from_vehicle, name="create_post_from_vehicle"),
    path("<int:post_id>/review/", review_post, name="review_post"),
    path("<int:post_id>/real-publish-check/", real_publish_check, name="real_publish_check"),
    path("<int:post_id>/approve/", approve_post, name="approve_post"),
    path("<int:post_id>/publish/", publish_post, name="publish_post"),
    path(
        "<int:post_id>/publish-instagram-real/",
        publish_instagram_real,
        name="publish_instagram_real",
    ),
    path(
        "<int:post_id>/publish-all-real/",
        publish_all_real,
        name="publish_all_real",
    ),
    path("<int:post_id>/save-review/", save_review_post, name="save_review_post"),
]
