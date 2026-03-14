"""
CeleryDispatcher — production CheckDispatcher implementation.

Enqueues checks to RabbitMQ via Celery. Used when dispatch_mode == "celery".
"""
import logging
from typing import Any

from celery.result import AsyncResult

from datametronome_podium.core.celery_app import QUEUE_HIGH
from datametronome_podium.core.check_dispatcher import CheckDispatcher, JobStatus
from datametronome_podium.tasks.check_tasks import execute_check

logger = logging.getLogger(__name__)

# Map Celery states to our JobStatus enum
_STATE_MAP = {
    "PENDING": JobStatus.PENDING,
    "RECEIVED": JobStatus.PENDING,
    "STARTED": JobStatus.RUNNING,
    "SUCCESS": JobStatus.COMPLETED,
    "FAILURE": JobStatus.FAILED,
    "REVOKED": JobStatus.FAILED,
    "RETRY": JobStatus.RUNNING,
}


class CeleryDispatcher:
    """Dispatch checks via Celery task queue.

    By default, dispatches to checks.high (user is waiting).
    Beat uses celery_app.send_task() directly with checks.default.
    """

    def __init__(self, default_queue: str = QUEUE_HIGH) -> None:
        self._default_queue = default_queue

    async def dispatch(self, clef_id: str) -> str:
        result = execute_check.apply_async(
            args=[clef_id],
            queue=self._default_queue,
        )
        logger.info("Dispatched check clef=%s job_id=%s queue=%s",
                     clef_id, result.id, self._default_queue)
        return result.id

    async def get_status(self, job_id: str) -> JobStatus:
        result = AsyncResult(job_id)
        return _STATE_MAP.get(result.state, JobStatus.PENDING)

    async def get_result(self, job_id: str) -> dict[str, Any] | None:
        result = AsyncResult(job_id)
        if not result.ready():
            return None
        return result.result
