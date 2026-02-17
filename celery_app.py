"""
Celery Application Configuration for AnalytIQ
Handles async task processing for PDF operations and email sending
"""

from celery import Celery
import config

# Redis URL for broker and result backend
REDIS_URL = config.REDIS_URL

# Initialize Celery
celery_app = Celery(
    "analytiq", broker=REDIS_URL, backend=REDIS_URL, include=["tasks"]  # Import tasks module
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
    "tasks.process_pdf_and_extract_text": {"queue": "pdf_processing"},
    "tasks.generate_exercises_async": {"queue": "ai_tasks"},
    "tasks.send_email_async": {"queue": "emails"},
}

if __name__ == "__main__":
    celery_app.start()
