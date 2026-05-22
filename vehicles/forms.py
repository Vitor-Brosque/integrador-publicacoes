from django import forms

from vehicles.models import Vehicle


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


class VehicleCreateForm(forms.Form):
    raw_input = forms.CharField(
        label="Dados do veículo",
        widget=forms.Textarea(
            attrs={
                "rows": 12,
                "placeholder": "Cole aqui os dados do veículo...",
            }
        ),
    )

    media_files = MultipleFileField(
        label="Mídias do veículo",
        required=False,
    )


class VehicleEditForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["raw_input"]
        widgets = {
            "raw_input": forms.Textarea(
                attrs={
                    "rows": 12,
                    "placeholder": "Cole aqui os dados do veículo...",
                }
            )
        }


class VehicleMediaUploadForm(forms.Form):
    media_files = MultipleFileField(
        label="Mídias",
        required=True,
    )
