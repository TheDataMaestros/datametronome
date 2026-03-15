"""Tests for intelligence Celery tasks."""
import pytest
from unittest.mock import AsyncMock


from datametronome_podium.tasks.intelligence_tasks import (
    _acquire_lock,
    _release_lock,
    prune_old_snapshots,
)


def test_prune_task_exists():
    assert prune_old_snapshots is not None
    assert prune_old_snapshots.name == "datametronome.prune_old_snapshots"


def test_aggregate_weekly_snapshots():
    """Pruning should create weekly aggregates before deleting old snapshots."""
    from datametronome_podium.tasks.intelligence_tasks import _aggregate_weekly_snapshots
    import json

    snapshots = [
        {"id": "s1", "stave_id": "stave-1", "table_metrics": json.dumps({"t1": {"row_count": 100}}), "captured_at": "2026-01-01T00:00:00Z"},
        {"id": "s2", "stave_id": "stave-1", "table_metrics": json.dumps({"t1": {"row_count": 200}}), "captured_at": "2026-01-02T00:00:00Z"},
    ]
    result = _aggregate_weekly_snapshots(snapshots)
    assert len(result) >= 1
    assert result[0]["snapshot_type"] == "weekly_aggregate"


@pytest.mark.asyncio
async def test_acquire_lock_success():
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)
    result = await _acquire_lock(mock_redis, "stave-1")
    assert result is True
    mock_redis.set.assert_called_once_with(
        "intelligence:lock:stave-1", "1", nx=True, ex=1800,
    )


@pytest.mark.asyncio
async def test_acquire_lock_already_held():
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=False)
    result = await _acquire_lock(mock_redis, "stave-1")
    assert result is False


@pytest.mark.asyncio
async def test_release_lock():
    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(return_value=1)
    await _release_lock(mock_redis, "stave-1")
    mock_redis.delete.assert_called_once_with("intelligence:lock:stave-1")
