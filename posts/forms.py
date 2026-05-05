from django import forms

from vehicles.models import Vehicle


PLATFORM_CHOICES = [
    ("instagram", "Instagram"),
    ("facebook", "Facebook"),
    ("tiktok", "TikTok"),
    ("youtube", "YouTube"),
    ("google_business", "Google Business"),
]


POST_TYPE_CHOICES = [
    ("single_image", "Foto única"),
    ("carousel", "Carrossel"),
    ("video", "Vídeo"),
]


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            return [single_file_clean(file, initial) for file in data]

        return single_file_clean(data, initial)


class CreatePostForm(forms.Form):
    raw_input = forms.CharField(
        label="Dados do veículo",
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "placeholder": "Cole aqui os dados do veículo...",
            }
        ),
    )

    media_files = MultipleFileField(
        label="Fotos ou vídeos",
        required=False,
    )


class CreatePostFromVehicleForm(forms.Form):
    vehicle = forms.ModelChoiceField(
        label="Veículo",
        queryset=Vehicle.objects.all().order_by("-created_at"),
    )

    post_type = forms.ChoiceField(
        label="Tipo de post",
        choices=POST_TYPE_CHOICES,
        initial="carousel",
    )

    media_asset_ids = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    platforms = forms.MultipleChoiceField(
        label="Plataformas",
        choices=PLATFORM_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        initial=["instagram", "facebook"],
    )
