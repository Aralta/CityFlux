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
        
        # Configuration Celery
        CELERY_BROKER_URL=os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0'),
        CELERY_RESULT_BACKEND=os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
        CELERY_ACCEPT_CONTENT=['json'],
        CELERY_TASK_SERIALIZER='json',
        CELERY_RESULT_SERIALIZER='json',
        CELERY_TIMEZONE='UTC',
    )

django.setup()

# Import Celery app pour le rendre accessible
from celery_app import app as celery_app

from views.carte import carte_view, api_search, api_layers_list, api_layer_data, api_layer_config
from views.handler import database_console, index, health_check, spark_upper , render_enhanced_data, conversion_view, compute_view, compute_wiki_view
from views.get_enhanced_data import GetEnchancedData
from views.docker_console import multi_console_view, get_docker_logs, get_all_containers_status
from views.conversion_api import trigger_conversion_job


urlpatterns = [
    # Pages principales
    path('', index, name='index'),
    path('carte/', carte_view, name='carte'),
    path('db-console/', database_console, name='database_console'),
    path('spark-upper/', spark_upper, name='spark_upper'),
    path('enhanced-data/', render_enhanced_data, name='enhanced_data'),
    path('multi-console/', multi_console_view, name='multi_console'),
    path('conversion/', conversion_view, name='conversion_page'),
    path('compute/', compute_view, name='compute'),
    path('compute/wiki/', compute_wiki_view, name='compute_wiki'),
    
    # API
    path('health/', health_check, name='health_check'),
    path('api/search', api_search, name='api_search'),
    path('api/layers/', api_layers_list, name='api_layers_list'),
    path('api/layers/<str:layer_id>/data/', api_layer_data, name='api_layer_data'),
    path('api/layers/<str:layer_id>/config/', api_layer_config, name='api_layer_config'),
    path('api/enhanced-data/', GetEnchancedData, name='api_enhanced_data'),
    path('api/docker-logs/<str:service_id>/', get_docker_logs, name='api_docker_logs'),
    path('api/docker-status/', get_all_containers_status, name='api_docker_status'),
    path('api/conversion/trigger/', trigger_conversion_job, name='api_trigger_conversion'),
]


if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.argv += ['runserver', '8000']
    execute_from_command_line(sys.argv)
