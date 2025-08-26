from django import forms


SITE_CHOICES = [
    ("animeunity", "AnimeUnity"),
    ("streamingcommunity", "StreamingCommunity"),
]


class SearchForm(forms.Form):
    site = forms.ChoiceField(
        choices=SITE_CHOICES,
        label="Sito",
        widget=forms.Select(
            attrs={
                "class": "block w-full appearance-none rounded-lg border border-gray-300 bg-white py-3 pl-12 pr-12 text-gray-900 placeholder-gray-500 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500",
            }
        ),
    )
    query = forms.CharField(
        max_length=200,
        label="Cosa cerchi?",
        widget=forms.TextInput(
            attrs={
                "class": "block w-full rounded-lg border border-gray-300 bg-white py-3 pl-12 pr-12 text-gray-900 placeholder-gray-500 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500",
                "placeholder": "Cerca titolo...",
                "autocomplete": "off",
            }
        ),
    )


class DownloadForm(forms.Form):
    source_alias = forms.CharField(widget=forms.HiddenInput)
    item_payload = forms.CharField(widget=forms.HiddenInput)
    # Opzionali per serie
    season = forms.CharField(max_length=10, required=False, label="Stagione")
    episode = forms.CharField(max_length=20, required=False, label="Episodio (es: 1-3)")
