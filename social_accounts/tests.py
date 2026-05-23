from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import SocialAccount, SocialAccountStatus
from .services import build_readiness


class SocialAccountIntegrationViewsTests(TestCase):
    def setUp(self):
        self.platforms = [
            ("instagram", "instagram"),
            ("facebook", "facebook"),
            ("google-business", "google_business"),
            ("youtube", "youtube"),
            ("tiktok", "tiktok"),
        ]

    def platform_url(self, slug):
        return reverse("social_accounts:platform_integration", kwargs={"platform_slug": slug})

    def test_integrations_dashboard_returns_200(self):
        response = self.client.get(reverse("social_accounts:integrations_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integrações sociais")

    def test_platform_pages_return_200(self):
        for slug, _platform in self.platforms:
            response = self.client.get(self.platform_url(slug))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Salvar configuração")

    def test_platform_post_creates_social_account(self):
        token_expires_at = (timezone.now() + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M")

        for slug, platform in self.platforms:
            response = self.client.post(
                self.platform_url(slug),
                data={
                    "account_name": f"Conta {platform}",
                    "status": SocialAccountStatus.CONNECTED,
                    "external_account_id": f"{platform}-external-id",
                    "page_id": f"{platform}-page-id",
                    "access_token": f"{platform}-token",
                    "token_expires_at": token_expires_at,
                    "metadata": "{\"scope\": \"publish\"}",
                },
            )

            self.assertEqual(response.status_code, 302)
            account = SocialAccount.objects.get(platform=platform)
            self.assertEqual(account.account_name, f"Conta {platform}")
            self.assertEqual(account.status, SocialAccountStatus.CONNECTED)
            self.assertEqual(account.external_account_id, f"{platform}-external-id")
            self.assertEqual(account.page_id, f"{platform}-page-id")
            self.assertEqual(account.access_token, f"{platform}-token")
            self.assertEqual(account.metadata, {"scope": "publish"})

    def test_platform_post_edits_social_account_and_preserves_token_when_blank(self):
        account = SocialAccount.objects.create(
            platform="instagram",
            account_name="Conta antiga",
            status=SocialAccountStatus.CONNECTED,
            external_account_id="old-external-id",
            access_token="old-secret-token",
            page_id="old-page-id",
            metadata={"scope": "old"},
        )

        response = self.client.post(
            self.platform_url("instagram"),
            data={
                "account_name": "Conta nova",
                "status": SocialAccountStatus.CONNECTED,
                "external_account_id": "new-external-id",
                "page_id": "new-page-id",
                "access_token": "",
                "token_expires_at": "",
                "metadata": "{\"scope\": \"new\"}",
            },
        )

        self.assertEqual(response.status_code, 302)
        account.refresh_from_db()
        self.assertEqual(account.account_name, "Conta nova")
        self.assertEqual(account.external_account_id, "new-external-id")
        self.assertEqual(account.page_id, "new-page-id")
        self.assertEqual(account.access_token, "old-secret-token")
        self.assertEqual(account.metadata, {"scope": "new"})

    def test_readiness_flags_ready_and_incomplete_states(self):
        ready_account = SocialAccount.objects.create(
            platform="youtube",
            account_name="YouTube Ready",
            status=SocialAccountStatus.CONNECTED,
            external_account_id="channel-123",
            access_token="token-ready",
        )
        incomplete_account = SocialAccount.objects.create(
            platform="tiktok",
            account_name="TikTok Incompleto",
            status=SocialAccountStatus.CONNECTED,
            external_account_id="",
            access_token="",
        )

        ready_state = build_readiness(ready_account)
        incomplete_state = build_readiness(incomplete_account)

        self.assertTrue(ready_state["is_ready"])
        self.assertFalse(incomplete_state["is_ready"])
        self.assertIn("external_account_id", incomplete_state["fields_missing"])
        self.assertIn("access_token", incomplete_state["fields_missing"])

        response = self.client.get(reverse("social_accounts:integrations_dashboard"))
        self.assertContains(response, "pronto")
        self.assertContains(response, "incompleto")

    def test_token_is_not_rendered_in_listings(self):
        secret_token = "super-secret-token"
        SocialAccount.objects.create(
            platform="facebook",
            account_name="Conta Facebook",
            status=SocialAccountStatus.CONNECTED,
            external_account_id="page-123",
            access_token=secret_token,
        )

        dashboard_response = self.client.get(reverse("social_accounts:integrations_dashboard"))
        platform_response = self.client.get(self.platform_url("facebook"))

        self.assertNotContains(dashboard_response, secret_token)
        self.assertNotContains(platform_response, secret_token)
        self.assertContains(platform_response, "token preenchido")
