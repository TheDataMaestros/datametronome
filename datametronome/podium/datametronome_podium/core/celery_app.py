"""
Celery application configuration for DataMetronome workers.

Broker: RabbitMQ (amqp://)
Result backend: Redis (redis://)
Scheduler: celery-redbeat (reads schedules from Redis)
"""
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from datametronome_podium.core.config import settings

# Queue names
QUEUE_HIGH = "checks.high"
QUEUE_DEFAULT = "checks.default"
QUEUE_BULK = "checks.bulk"
QUEUE_DLQ = "checks.dlq"
QUEUE_INTELLIGENCE = "intelligence.default"

celery_app = Celery(
    "datametronome",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Queues
    task_queues=(
        Queue(QUEUE_HIGH, routing_key="checks.high"),
        Queue(QUEUE_DEFAULT, routing_key="checks.default"),
        Queue(QUEUE_BULK, routing_key="checks.bulk"),
        Queue(QUEUE_DLQ, routing_key="checks.dlq"),
        Queue(QUEUE_INTELLIGENCE, routing_key="intelligence.default"),
    ),
    task_default_queue=QUEUE_DEFAULT,

    # Routing (task name matches the name= in @celery_app.task decorator)
    task_routes={
        "datametronome.execute_check": {"queue": QUEUE_DEFAULT},
        "datametronome.run_auto_scan": {"queue": QUEUE_INTELLIGENCE},
        "datametronome.run_daily_intelligence": {"queue": QUEUE_INTELLIGENCE},
        "datametronome.run_on_demand_analysis": {"queue": QUEUE_INTELLIGENCE},
        "datametronome.prune_old_snapshots": {"queue": QUEUE_DEFAULT},
        "datametronome.olist_simulate_ingestion": {"queue": QUEUE_INTELLIGENCE},
        "datametronome.run_daily_intelligence_all_staves": {"queue": QUEUE_INTELLIGENCE},
    },

    # Retry defaults
    task_default_retry_delay=10,
    task_max_retries=3,

    # Acks late so unfinished tasks are redelivered on crash
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Concurrency
    worker_concurrency=settings.celery_concurrency,

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # RedBeat scheduler (used by celery beat)
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=settings.redis_url,
)

# Explicitly include task modules (autodiscover expects tasks.py, ours is check_tasks.py)
celery_app.conf.include = [
    "datametronome_podium.tasks.check_tasks",
    "datametronome_podium.tasks.intelligence_tasks",
    "datametronome_podium.tasks.olist_simulation",
]

# ── Periodic schedules (celery-redbeat reads these from conf on startup) ────
celery_app.conf.beat_schedule = {
    # Simulate new Olist orders every 4 hours so the AI sees live data flow
    "olist-simulate-ingestion-every-4h": {
        "task": "datametronome.olist_simulate_ingestion",
        "schedule": crontab(minute=0, hour="*/4"),
        "options": {"queue": "intelligence.default"},
    },
    # Re-run the full intelligence pipeline across all staves daily at 06:00 UTC
    "daily-intelligence-all-staves": {
        "task": "datametronome.run_daily_intelligence_all_staves",
        "schedule": crontab(minute=0, hour=6),
        "options": {"queue": "intelligence.default"},
    },
    # Weekly snapshot pruning (Sundays 03:00 UTC)
    "prune-old-snapshots-weekly": {
        "task": "datametronome.prune_old_snapshots",
        "schedule": crontab(minute=0, hour=3, day_of_week=0),
        "options": {"queue": "checks.default"},
    },
}
