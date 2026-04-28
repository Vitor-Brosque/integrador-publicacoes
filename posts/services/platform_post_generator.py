from posts.models import Platform, PlatformPost, SocialPost


def generate_platform_posts(social_post: SocialPost):
    vehicle = social_post.vehicle

    platform_content = {
        Platform.INSTAGRAM: {
            "caption": (
                f"{social_post.base_caption}\n\n"
                f"Disponível na Rodoviária Veículos.\n"
                f"Chame no WhatsApp para mais informações."
            ),
            "hashtags": "#carros #bauru #rodoviariaveiculos",
        },
        Platform.FACEBOOK: {
            "caption": (
                f"{social_post.base_caption}\n\n"
                f"Veículo disponível para visita na loja.\n"
                f"Entre em contato para saber mais."
            ),
            "hashtags": "#RodoviariaVeiculos #Bauru",
        },
        Platform.TIKTOK: {
            "caption": (
                f"{vehicle.brand} {vehicle.model} passando na sua tela.\n"
                f"Quer saber mais? Chama a gente."
            ),
            "hashtags": "#carros #carrosembauru",
        },
        Platform.YOUTUBE: {
            "title": f"{vehicle.brand} {vehicle.model} disponível em Bauru",
            "description": (
                f"{social_post.base_caption}\n\n"
                f"Rodoviária Veículos\n"
                f"Av. Nações Unidas 1-50, Bauru\n"
                f"WhatsApp (14) 99711-2299"
            ),
            "hashtags": "#carros #bauru",
        },
        Platform.GOOGLE_BUSINESS: {
            "title": f"{vehicle.brand} {vehicle.model} disponível",
            "description": (
                f"{vehicle.brand} {vehicle.model} disponível na Rodoviária Veículos.\n"
                f"Consulte condições e agende sua visita.\n\n"
                f"Av. Nações Unidas 1-50, Bauru\n"
                f"WhatsApp (14) 99711-2299"
            ),
        },
    }

    platform_posts = []

    for platform, content in platform_content.items():
        platform_post, _created = PlatformPost.objects.update_or_create(
            social_post=social_post,
            platform=platform,
            defaults={
                "title": content.get("title", ""),
                "caption": content.get("caption", ""),
                "description": content.get("description", ""),
                "hashtags": content.get("hashtags", ""),
                "generated_by_ai": True,
            },
        )
        platform_posts.append(platform_post)

    return platform_posts
