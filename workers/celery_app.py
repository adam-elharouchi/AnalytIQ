"""
Celery Application Configuration for AnalytIQ
Handles async task processing for PDF operations and email sending
"""

from celery import Celery
from celery.schedules import crontab
import config

# Redis URL for broker and result backend
REDIS_URL = config.REDIS_URL

# Initialize Celery
celery_app = Celery(
    "analytiq",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["workers.tasks"],  # Import tasks module
)

# Celery Configuration
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={"master_name": "mymaster"},
    # Worker configuration
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Task routes (optional - for multiple queues)
celery_app.conf.task_routes = {
    "workers.tasks.process_pdf_and_extract_text": {"queue": "pdf_processing"},
    "workers.tasks.generate_exercises_async": {"queue": "ai_tasks"},
    "workers.tasks.send_email_async": {"queue": "emails"},
    "workers.tasks.compute_exercise_quality_scores": {"queue": "ai_tasks"},
}

# Periodic task schedule (requires celery beat)
celery_app.conf.beat_schedule = {
    "cleanup-expired-lti-sessions-daily": {
        "task": "workers.tasks.cleanup_expired_lti_sessions",
        "schedule": 86400,  # once per day (seconds)
    },
    "compute-exercise-quality": {
        "task": "workers.tasks.compute_exercise_quality_scores",
        "schedule": crontab(hour="*/6"),  # every 6 hours
        "options": {"queue": "ai_tasks"},
    },
}

if __name__ == "__main__":
    celery_app.start()
