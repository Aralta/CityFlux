#!/usr/bin/env python3
"""
Application Django principale pour MobiFlux
Usage: python app.py runserver
"""
import os
import sys
from django.conf import settings
import django
from django.urls import path
from django.core.management import execute_from_command_line

BASE_DIR = os.path.dirname(__file__) or '.'

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='dev-secret-key-mobiflux',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        MIDDLEWARE=[
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
        ],
        INSTALLED_APPS=[
            'django.contrib.staticfiles',
            'django.contrib.contenttypes',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ.get('POSTGRES_DB', 'mobilite_urbaine'),
                'USER': os.environ.get('POSTGRES_USER', 'admin'),
                'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'admin'),
                'HOST': os.environ.get('SQL_HOST', 'db'),
                'PORT': os.environ.get('SQL_PORT', '5432'),
            }
        },
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(BASE_DIR, 'templates')],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.template.context_processors.csrf',
                ],
            },
        }],
        STATIC_URL='/static/',
        STATICFILES_DIRS=[os.path.join(BASE_DIR, 'static')],
    )

django.setup()

from views.carte import carte_view, api_search, api_layers_list, api_layer_data, api_layer_config
from views.handler import database_console, index, health_check, spark_upper

urlpatterns = [
    # Pages principales
    path('', index, name='index'),
    path('carte/', carte_view, name='carte'),
    path('db-console/', database_console, name='database_console'),
    path('spark-upper/', spark_upper, name='spark_upper'),
    
    # API
    path('health/', health_check, name='health_check'),
    path('api/search', api_search, name='api_search'),
    path('api/layers/', api_layers_list, name='api_layers_list'),
    path('api/layers/<str:layer_id>/data/', api_layer_data, name='api_layer_data'),
    path('api/layers/<str:layer_id>/config/', api_layer_config, name='api_layer_config'),
]

if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.argv += ['runserver', '8000']
    execute_from_command_line(sys.argv)
