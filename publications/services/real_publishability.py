def get_real_publishability(platform: str, post_type: str) -> tuple[str, list[str]]:
    if platform == "instagram":
        return "ready", []

    if platform == "facebook":
        if post_type == "single_image":
            return "ready", []
        if post_type == "carousel":
            return "blocked", [
                "Facebook carousel real ainda não está implementado nesta versão.",
            ]
        if post_type == "video":
            return "blocked", [
                "Facebook video real ainda não está implementado nesta versão.",
            ]
        return "blocked", [
            f"Tipo de post não suportado para Facebook real: {post_type}.",
        ]

    if platform == "google_business":
        if post_type == "single_image":
            return "ready", []
        if post_type == "carousel":
            return "warning", [
                "Google Business will publish using the first image only.",
            ]
        if post_type == "video":
            return "blocked", [
                "Google Business real publishing does not support video in this version.",
            ]
        return "blocked", [
            f"Tipo de post não suportado para Google Business real: {post_type}.",
        ]

    if platform == "youtube":
        return "blocked", [
            "YouTube requer OAuth e upload via videos.insert; publisher real ainda não está ativo.",
        ]

    if platform == "tiktok":
        return "blocked", [
            "TikTok requer app/scopes e fluxo de direct post; publisher real ainda não está ativo.",
        ]

    return "blocked", [
        f"Publisher real sem suporte para a plataforma: {platform}.",
    ]
