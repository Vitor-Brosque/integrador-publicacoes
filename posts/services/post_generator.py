from posts.models import SocialPost


def generate_social_post(vehicle):
    title = f"{vehicle.brand} {vehicle.model} disponível"

    caption = (
        f"{vehicle.brand} {vehicle.model} {vehicle.version or ''}\n"
        f"Ótima opção para o dia a dia.\n"
        f"Entre em contato para mais informações."
    )

    post = SocialPost.objects.create(
        vehicle=vehicle,
        base_title=title,
        base_caption=caption,
        generated_by_ai=True,
        generation_status="basic",
    )

    return post
