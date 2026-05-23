import json

from django import forms

from .models import SocialAccountStatus


class SocialAccountIntegrationForm(forms.Form):
    account_name = forms.CharField(
        label="account_name",
        max_length=160,
    )
    status = forms.ChoiceField(
        label="status",
        choices=SocialAccountStatus.choices,
    )
    external_account_id = forms.CharField(
        label="external_account_id",
        max_length=255,
        required=False,
    )
    page_id = forms.CharField(
        label="page_id",
        max_length=255,
        required=False,
    )
    access_token = forms.CharField(
        label="access_token",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Deixe em branco para preservar o token atual na edição.",
    )
    token_expires_at = forms.DateTimeField(
        label="token_expires_at",
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )
    metadata = forms.CharField(
        label="metadata",
        required=False,
        widget=forms.Textarea(attrs={"rows": 6}),
        help_text="JSON válido. Exemplo: {\"scope\": \"publish\"}",
    )

    def clean_metadata(self):
        raw_value = self.cleaned_data.get("metadata") or ""
        if not raw_value.strip():
            return {}

        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("Metadata precisa ser um JSON válido.") from exc

        if not isinstance(value, dict):
            raise forms.ValidationError("Metadata precisa ser um objeto JSON.")

        return value

    def save(self, instance, platform):
        instance.platform = platform
        instance.account_name = self.cleaned_data["account_name"]
        instance.status = self.cleaned_data["status"]
        instance.external_account_id = self.cleaned_data["external_account_id"] or None
        instance.page_id = self.cleaned_data["page_id"] or None
        instance.token_expires_at = self.cleaned_data["token_expires_at"]
        instance.metadata = self.cleaned_data["metadata"] or {}

        access_token = self.cleaned_data.get("access_token")
        if access_token:
            instance.access_token = access_token
        elif instance.pk is None:
            instance.access_token = None

        instance.save()
        return instance
