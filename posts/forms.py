from django import forms


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
