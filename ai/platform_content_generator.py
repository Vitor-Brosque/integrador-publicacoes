from ai.fake_client import fake_generate_platform_content
from ai.schemas import GeneratedPlatformContent


def generate_platform_content(social_post) -> list[GeneratedPlatformContent]:
    return fake_generate_platform_content(social_post)
