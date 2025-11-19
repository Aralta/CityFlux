#!/usr/bin/env python3
"""
Script Django minimal pour la page Carte Interactive MobiFlux
Usage: python test.py runserver
"""
import os
import sys
from django.conf import settings
import django
from django.urls import path
from django.core.management import execute_from_command_line

BASE_DIR = os.path.dirname(__file__) or '.'

# Configuration Django
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='dev-secret-key-mobiflux-carte',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        MIDDLEWARE=[
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
        ],
        INSTALLED_APPS=[
            'django.contrib.staticfiles',
        ],
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(BASE_DIR, 'templates')],
            'APP_DIRS': True,
            'OPTIONS': {},
        }],
        STATIC_URL='/static/',
        STATICFILES_DIRS=[os.path.join(BASE_DIR, 'static')],
    )

django.setup()

# Import des vues de la carte
from views.carte import (
    carte_view, 
    api_search, 
    api_layers_list, 
    api_layer_data, 
    api_layer_config
)

# Routes - Seulement la page carte interactive
urlpatterns = [
    # Page principale - redirection vers la carte
    path('', carte_view),
    
    # Page de carte interactive
    path('carte/', carte_view),
    
    # API endpoints pour la carte
    path('api/search', api_search),
    path('api/layers/', api_layers_list),
    path('api/layers/<str:layer_id>/data/', api_layer_data),
    path('api/layers/<str:layer_id>/config/', api_layer_config),
]

# Entrée principale pour utiliser manage commands (runserver, etc.)
if __name__ == '__main__':
    # Si l'utilisateur n'a pas passé d'argument, on fournit runserver par défaut.
    if len(sys.argv) == 1:
        sys.argv += ['runserver', '8000']
    execute_from_command_line(sys.argv)
