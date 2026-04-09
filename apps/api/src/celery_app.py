"""Celery application configuration"""

import os
from celery import Celery
from kombu import Exchange, Queue

# Initialize Celery app
app = Celery(
    "incident_triage",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)

# ============================================================================
# Configure Celery
# ============================================================================

app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Retry configuration
    task_acks_late=True,  # Tasks acknowledged after execution
    task_reject_on_worker_lost=True,  # Reject if worker dies
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_compression="gzip",
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Process 1 task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_pool='solo',  # Use solo pool for Windows compatibility
    
    # Queue routing
    task_queues=(
        Queue(
            "default",
            Exchange("default", type="direct"),
            routing_key="default",
        ),
        Queue(
            "clustering",
            Exchange("clustering", type="direct"),
            routing_key="clustering",
        ),
        Queue(
            "dead_letter",
            Exchange("dead_letter", type="direct"),
            routing_key="dead_letter",
        ),
    ),
    
    # Task routing
    task_routes={
        "tasks.cluster_logs": {"queue": "clustering"},
        "tasks.handle_dead_letter": {"queue": "dead_letter"},
    },
)

# ============================================================================
# Celery autodiscover
# ============================================================================

# Import tasks
from . import tasks  # noqa: F401, E402
