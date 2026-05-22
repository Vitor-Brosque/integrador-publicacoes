from publications.integrations.real_publishers.base import BaseRealPublisher


class FacebookRealPublisher(BaseRealPublisher):
    platform_name = "facebook"

    def _publish(self, publication_target):
        self.validate_common(publication_target)

        social_account = publication_target.social_account
        if not (social_account.page_id or social_account.external_account_id):
            raise ValueError("Facebook precisa de page_id ou external_account_id preenchido.")

        raise NotImplementedError("Publicação real para facebook ainda não implementada.")

