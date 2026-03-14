"""
CheckDispatcher protocol — the boundary between callers and check execution.

Agents, API endpoints, and the scheduler use this protocol.
They never import Celery directly. Implementations:
  - InlineDispatcher: showcase/SQLite mode, executes immediately
  - CeleryDispatcher: production, enqueues to RabbitMQ
  - RemoteDispatcher: hybrid agent, executes locally + pushes results
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Protocol, runtime_checkable


class JobStatus(Enum):
    """Status of a dispatched check job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@runtime_checkable
class CheckDispatcher(Protocol):
    """Protocol for dispatching check execution."""

    async def dispatch(self, clef_id: str) -> str:
        """Enqueue a check. Returns a job_id for tracking."""
        ...

    async def get_status(self, job_id: str) -> JobStatus:
        """Check if a job is pending, running, or done."""
        ...

    async def get_result(self, job_id: str) -> dict[str, Any] | None:
        """Get the result once complete. Returns None if not yet done."""
        ...


import json
import logging
import uuid
from datetime import datetime, timezone

from datametronome_podium.core.database import get_executor
from datametronome_podium.services.clef_executor import ClefExecutor
from datametronome_podium.services.stave_service import deserialize_clef, deserialize_stave

logger = logging.getLogger(__name__)


class InlineDispatcher:
    """Execute checks immediately in the current process. No broker needed.

    Used in showcase/SQLite mode and as the default when no broker is configured.

    NOTE: This class stores job results in instance-level dicts. The dispatcher
    factory must return a singleton (not a new instance per request) so that
    get_status/get_result can find jobs dispatched by earlier requests.
    """

    def __init__(self) -> None:
        self._results: dict[str, dict[str, Any]] = {}
        self._statuses: dict[str, JobStatus] = {}

    async def dispatch(self, clef_id: str) -> str:
        job_id = str(uuid.uuid4())
        self._statuses[job_id] = JobStatus.RUNNING

        try:
            executor = get_executor()

            # Fetch clef (QueryExecutor.query uses ? placeholders, QueryAdapter translates)
            clef_rows = await executor.query(
                "SELECT * FROM clefs WHERE id = ?", [clef_id]
            )
            if not clef_rows:
                raise ValueError(f"Clef not found: {clef_id}")
            clef = deserialize_clef(clef_rows[0])

            # Fetch stave
            stave_rows = await executor.query(
                "SELECT * FROM staves WHERE id = ?", [clef.stave_id]
            )
            if not stave_rows:
                raise ValueError(f"Stave not found: {clef.stave_id}")
            stave = deserialize_stave(stave_rows[0])

            # Execute
            clef_executor = ClefExecutor()
            result = await clef_executor.execute_clef(clef, stave)

            # Store check in DB
            metadata_for_storage = dict(result.metadata or {})
            metadata_for_storage["observed_value"] = result.observed_value
            check_id = f"check-{clef_id}-{datetime.now(timezone.utc).isoformat()}"

            await executor.insert("checks", {
                "id": check_id,
                "stave_id": stave.id,
                "clef_id": clef.id,
                "check_type": clef.check_type,
                "status": result.status,
                "message": result.message,
                "details": json.dumps(metadata_for_storage),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "execution_time": result.execution_time,
                "anomalies_count": result.anomalies_count,
                "severity": result.severity.value,
            })

            self._statuses[job_id] = JobStatus.COMPLETED
            self._results[job_id] = {
                "clef_id": clef.id,
                "stave_id": stave.id,
                "status": result.status,
                "message": result.message,
                "observed_value": result.observed_value,
                "execution_time": result.execution_time,
                "check_id": check_id,
            }

        except Exception as e:
            logger.error("InlineDispatcher failed for clef %s: %s", clef_id, e)
            self._statuses[job_id] = JobStatus.FAILED
            self._results[job_id] = {"error": str(e)}

        return job_id

    async def get_status(self, job_id: str) -> JobStatus:
        return self._statuses.get(job_id, JobStatus.FAILED)

    async def get_result(self, job_id: str) -> dict[str, Any] | None:
        return self._results.get(job_id)
