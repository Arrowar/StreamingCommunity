from django import forms


SITE_CHOICES = [
    ("animeunity", "AnimeUnity"),
    ("streamingcommunity", "StreamingCommunity"),
]


class SearchForm(forms.Form):
    site = forms.ChoiceField(choices=SITE_CHOICES, label="Sito")
    query = forms.CharField(max_length=200, label="Cosa cerchi?")


class DownloadForm(forms.Form):
    source_alias = forms.CharField(widget=forms.HiddenInput)
    item_payload = forms.CharField(widget=forms.HiddenInput)
    # Opzionali per serie
    season = forms.CharField(max_length=10, required=False, label="Stagione")
    episode = forms.CharField(max_length=20, required=False, label="Episodio (es: 1-3)")
