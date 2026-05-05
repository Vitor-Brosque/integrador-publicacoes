def validate_publication_target(publication_target):
    platform_post = publication_target.platform_post
    social_post = platform_post.social_post

    if publication_target.status != "pending":
        raise ValueError("A publicação precisa estar pendente para ser enviada.")

    if not hasattr(social_post, "review"):
        raise ValueError("O post não possui revisão.")

    if social_post.review.status != "approved":
        raise ValueError("O post precisa estar aprovado antes da publicação.")

    if not platform_post.generated_by_ai:
        raise ValueError("O conteúdo da plataforma ainda não foi gerado.")

    if publication_target.social_account is None:
        raise ValueError("A publicação precisa de uma conta social conectada.")   

    if publication_target.social_account.status != "connected":
        raise ValueError("A conta social precisa estar conectada.")    
   
    post_media_items = platform_post.social_post.post_media.all()

    for post_media in post_media_items:
        if not post_media.media_asset.public_url:
            raise ValueError("Todas as mídias do post precisam ter URL pública antes da publicação.")



    return True
