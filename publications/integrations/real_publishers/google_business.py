from publications.integrations.real_publishers.base import BaseRealPublisher


class GoogleBusinessRealPublisher(BaseRealPublisher):
    platform_name = "google_business"

    def _publish(self, publication_target):
        self.validate_common(publication_target)

        social_account = publication_target.social_account
        metadata = social_account.metadata or {}
        location_name = social_account.external_account_id or metadata.get("location_name")
        if not location_name:
            raise ValueError("Google Business precisa de external_account_id ou metadata['location_name'].")

        raise NotImplementedError("Publicação real para google_business ainda não implementada.")
