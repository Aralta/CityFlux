# views/admin.py  ← VERSION FINALE 100% FONCTIONNELLE

import os
import requests
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import connection
from imports.models import ApiSource, ApiFieldMapping


# ——— FONCTION DYNAMIQUE POUR LES COLONNES DE LA BDD ———
def get_available_db_fields():
    tables = ["arret", "ligne", "poi", "zone", "type_transport", "type_poi"]
    fields = []
    with connection.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """, [table])
                for (col,) in cursor.fetchall():
                    fields.append(f"{table}.{col}")
            except:
                continue
    return sorted(fields)


# ——— RÉCUPÉRATION DES CHAMPS DE L'API ———
def get_api_fields(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return list(data[0].keys())
        elif isinstance(data, dict):
            return list(data.keys())
        return []
    except Exception as e:
        print(f"Erreur API: {e}")
        return []


# ——— PAGE DE MAPPING ———
def admin_api_mapping(request, api_id):
    api = get_object_or_404(ApiSource, id=api_id)
    fields = get_api_fields(api.url)
    db_fields = get_available_db_fields()

    # Pré-remplissage des mappings existants
    current_mappings = {m.external_field: m.internal_field for m in api.mappings.all()}

    if request.method == "POST":
        for field in fields:
            selected = request.POST.get(field)
            if selected and selected.strip():
                ApiFieldMapping.objects.update_or_create(
                    api=api,
                    external_field=field,
                    defaults={"internal_field": selected}
                )
            else:
                ApiFieldMapping.objects.filter(api=api, external_field=field).delete()

        messages.success(request, "Mapping enregistré avec succès !")

        if "import_now" in request.POST:
            messages.info(request, "Importation déclenchée ! (en attente du service preprocess)")

        return redirect('admin_api_mapping', api_id=api.id)

    return render(request, "admin/admin_api_mapping.html", {
        "api": api,
        "fields": fields,
        "db_fields": db_fields,
        "current_mappings": current_mappings,
    })


# ——— LES AUTRES FONCTIONS (liste, ajout, suppression) ———
def admin_api_list(request):
    apis = ApiSource.objects.all().order_by('id')
    return render(request, "admin/api_list.html", {"apis": apis})

def admin_api_add(request):
    if request.method == "POST":
        name = request.POST.get("name")
        url = request.POST.get("url")
        description = request.POST.get("description", "")
        ApiSource.objects.create(name=name, url=url, description=description)
        messages.success(request, f"API '{name}' ajoutée !")
    return redirect('admin_api_list')

def admin_api_delete(request, api_id):
    api = get_object_or_404(ApiSource, id=api_id)
    api_name = api.name
    api.delete()
    messages.success(request, f"API '{api_name}' supprimée avec succès.")
    return redirect('admin_api_list')

def admin_dashboard(request):
    return render(request, "admin/admin.html")