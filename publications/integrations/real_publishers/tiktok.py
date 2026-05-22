from publications.integrations.real_publishers.base import BaseRealPublisher


class TikTokRealPublisher(BaseRealPublisher):
    platform_name = "tiktok"

    def _publish(self, publication_target):
        self.validate_common(publication_target)

        social_account = publication_target.social_account
        if not social_account.external_account_id:
            raise ValueError("TikTok precisa de external_account_id preenchido.")

        # TikTok Content Posting API exige app registrado, scopes e fluxo de upload/direct post.
        # Fotos ainda dependem de domínios/prefixos verificados conforme a documentação.
        raise NotImplementedError("Publicação real para tiktok ainda não implementada.")

