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


@pytest.mark.asyncio
async def test_acquire_lock_success():
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)
    token = await _acquire_lock(mock_redis, "stave-1")
    # Returns a non-empty hex token string on success
    assert isinstance(token, str)
    assert len(token) == 32
    call_kwargs = mock_redis.set.call_args
    assert call_kwargs.kwargs.get("nx") is True
    assert call_kwargs.kwargs.get("ex") == 1800
    assert call_kwargs.args[0] == "intelligence:lock:stave-1"


@pytest.mark.asyncio
async def test_acquire_lock_already_held():
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=False)
    result = await _acquire_lock(mock_redis, "stave-1")
    # Returns None when the lock is already held
    assert result is None


@pytest.mark.asyncio
async def test_release_lock_when_token_matches():
    mock_redis = AsyncMock()
    token = "abc123"
    mock_redis.get = AsyncMock(return_value=token.encode())
    mock_redis.delete = AsyncMock(return_value=1)
    await _release_lock(mock_redis, "stave-1", token)
    mock_redis.delete.assert_called_once_with("intelligence:lock:stave-1")


@pytest.mark.asyncio
async def test_release_lock_skipped_when_token_mismatch():
    """Lock should not be deleted if a different task holds it (e.g. after TTL expiry)."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=b"other-token")
    mock_redis.delete = AsyncMock()
    await _release_lock(mock_redis, "stave-1", "my-token")
    mock_redis.delete.assert_not_called()
