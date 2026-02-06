"""
TBot Celery Tasks Module.
Background tasks for TTS, vector sync, etc.
"""
import os
from celery import Celery

# Create Celery app
celery_app = Celery(
    "tbot_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "amqp://tbot:tbot123@localhost:5672//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=[
        "tasks.tts_tasks",
        "tasks.sync_tasks",
    ]
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    
    # Task settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result settings
    result_expires=3600,  # 1 hour
)

# Periodic tasks schedule (optional, requires celery beat)
celery_app.conf.beat_schedule = {
    "sync-vectors-daily": {
        "task": "tasks.sync_tasks.sync_all_regions",
        "schedule": 86400.0,  # Every 24 hours
    },
}
