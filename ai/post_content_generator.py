from ai.fake_client import fake_generate_post_content
from ai.schemas import GeneratedPostContent


def generate_post_content(vehicle) -> GeneratedPostContent:
    return fake_generate_post_content(vehicle)
