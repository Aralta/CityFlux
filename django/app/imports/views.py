import os
import pandas as pd
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .forms import ImportSelectForm
from .models import ImportJob, ApiSource

# utilitaire : champs attendus par table
def get_bdd_fields(table):
    schemas = {
        "arret": ["nom", "latitude", "longitude", "id_type"],
        "ligne": ["id", "nom", "id_type", "capacite"],
        "poi": ["nom", "latitude", "longitude", "type"],
        "zone": ["geom_geojson", "type"],
    }
    return schemas.get(table, [])

def import_upload(request):
    if request.method == "POST":
        form = ImportSelectForm(request.POST, request.FILES)
        if form.is_valid():
            api = form.cleaned_data["api"]
            fichier = form.cleaned_data["fichier"]
            table_cible = form.cleaned_data["table_cible"]

            job = ImportJob.objects.create(api=api, uploaded_file=fichier, table_cible=table_cible, status="en_attente")
            # lire le fichier temporairement pour récupérer les colonnes
            fp = job.uploaded_file.path
            try:
                if fp.lower().endswith(".csv"):
                    df = pd.read_csv(fp, nrows=5)
                elif fp.lower().endswith((".xls", ".xlsx")):
                    df = pd.read_excel(fp, nrows=5)
                else:
                    # tente GeoJSON / JSON
                    df = pd.read_json(fp)
                headers = list(df.columns)
            except Exception:
                headers = []

            return render(request, "admin/import_mapping.html", {
                "job": job,
                "colonnes": headers,
                "champs_bdd": get_bdd_fields(table_cible),
            })
    else:
        form = ImportSelectForm()
    return render(request, "admin/import_upload.html", {"form": form})

def import_mapping(request, job_id):
    job = get_object_or_404(ImportJob, id=job_id)
    if request.method == "POST":
        # construit mapping : mapping[bdd_field] = fichier_col
        mapping = {}
        for champ in get_bdd_fields(job.table_cible):
            val = request.POST.get(f"map_{champ}")
            if val:
                mapping[champ] = val
        job.mapping = mapping
        job.status = "en_cours"
        job.save()

        # Envoi au serveur de prétraitement
        preprocess_url = os.environ.get("PREPROCESS_URL", "http://preprocess:5000/process")
        files = {"file": open(job.uploaded_file.path, "rb")}
        payload = {
            "table": job.table_cible,
            "mapping": mapping,
            "api_url": job.api.url
        }
        try:
            r = requests.post(preprocess_url, files=files, data={"payload": pd.io.json.dumps(payload)})
            if r.status_code == 200:
                # on suppose que le prétraitement renvoie un JSON prêt pour insertion
                job.status = "termine"
                job.save()
                # tu peux également sauvegarder un rapport renvoyé par r.json()
                return redirect("import_result", job_id=job.id)
            else:
                job.status = "erreur"
                job.save()
                return redirect("import_result", job_id=job.id)
        except Exception as e:
            job.status = "erreur"
            job.save()
            return redirect("import_result", job_id=job.id)
    return redirect("import_upload")

def import_result(request, job_id):
    job = get_object_or_404(ImportJob, id=job_id)
    return render(request, "admin/import_result.html", {"job": job})
