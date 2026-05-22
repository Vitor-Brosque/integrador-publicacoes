from publications.integrations.real_publishers.base import BaseRealPublisher


class YouTubeRealPublisher(BaseRealPublisher):
    platform_name = "youtube"

    def _publish(self, publication_target):
        self.validate_common(publication_target)

        social_account = publication_target.social_account
        if not social_account.external_account_id:
            raise ValueError("YouTube precisa de external_account_id preenchido.")

        # YouTube exige OAuth e upload de vídeo via videos.insert.
        raise NotImplementedError("Publicação real para youtube ainda não implementada.")

