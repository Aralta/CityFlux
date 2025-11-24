from django import forms
from .models import ApiSource

TABLE_CHOICES = [
    ("arret", "Arrêts"),
    ("ligne", "Lignes"),
    ("poi", "POI"),
    ("zone", "Zones"),
]

class ImportSelectForm(forms.Form):
    api = forms.ModelChoiceField(queryset=ApiSource.objects.all())
    fichier = forms.FileField()
    table_cible = forms.ChoiceField(choices=TABLE_CHOICES)
