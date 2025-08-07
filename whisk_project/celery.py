import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whisk_project.settings')

app = Celery('whisk_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
