from django.db import models

class ApiSource(models.Model):
    name = models.TextField(unique=True)
    url = models.TextField()
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "api_registry"

class ImportJob(models.Model):
    STATUS_CHOICES = [
        ("en_attente", "En attente"),
        ("en_cours", "En cours"),
        ("termine", "Terminé"),
        ("erreur", "Erreur"),
    ]
    api = models.ForeignKey(ApiSource, on_delete=models.CASCADE)
    uploaded_file = models.FileField(upload_to="imports/")
    table_cible = models.CharField(max_length=50)
    mapping = models.JSONField(default=dict, blank=True)  # {"bdd_field":"file_col"}
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="en_attente")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_job"
