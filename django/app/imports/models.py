# imports/models.py 
from django.db import models

class ApiSource(models.Model):
    name = models.TextField(unique=True)
    url = models.TextField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class ImportJob(models.Model):
    STATUS_CHOICES = [
        ("en_attente", "En attente"),
        ("en_cours", "En cours"),
        ("termine", "Terminé"),
        ("erreur", "Erreur"),
    ]
    api = models.ForeignKey(ApiSource, on_delete=models.CASCADE)
    uploaded_file = models.FileField(upload_to="imports/", null=True, blank=True)
    table_cible = models.CharField(max_length=50)
    mapping = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="en_attente")
    created_at = models.DateTimeField(auto_now_add=True)


class ApiFieldMapping(models.Model):
    api = models.ForeignKey(ApiSource, on_delete=models.CASCADE, related_name="mappings")
    external_field = models.CharField(max_length=100)
    internal_field = models.CharField(max_length=100)

    class Meta:
        unique_together = ('api', 'external_field')

    def __str__(self):
        return f"{self.api.name}: {self.external_field} → {self.internal_field}"