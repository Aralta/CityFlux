import os
from celery import Celery

# Définir le module de settings Django par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.app')

# Créer l'instance Celery
app = Celery('app')

app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Paris',
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

# Découvrir les tâches dans tasks.py
app.autodiscover_tasks(['tasks'])

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
