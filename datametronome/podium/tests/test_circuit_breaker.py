"""Tests for stave circuit breaker."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_record_success_resets_counter():
    from datametronome_podium.core.circuit_breaker import StaveCircuitBreaker

    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock()
    cb = StaveCircuitBreaker(redis_client=mock_redis, threshold=5)

    await cb.record_success("stave-1")
    mock_redis.delete.assert_awaited_once_with("circuit:stave-1:failures")


@pytest.mark.asyncio
async def test_record_failure_increments():
    from datametronome_podium.core.circuit_breaker import StaveCircuitBreaker

    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=3)
    cb = StaveCircuitBreaker(redis_client=mock_redis, threshold=5)

    tripped = await cb.record_failure("stave-1")
    assert tripped is False
    mock_redis.incr.assert_awaited_once_with("circuit:stave-1:failures")


@pytest.mark.asyncio
async def test_record_failure_trips_at_threshold():
    from datametronome_podium.core.circuit_breaker import StaveCircuitBreaker

    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=5)
    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock()

    cb = StaveCircuitBreaker(redis_client=mock_redis, threshold=5, executor=mock_executor)

    tripped = await cb.record_failure("stave-1")
    assert tripped is True
    mock_executor.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_tripped():
    from datametronome_podium.core.circuit_breaker import StaveCircuitBreaker

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=b"5")
    cb = StaveCircuitBreaker(redis_client=mock_redis, threshold=5)

    assert await cb.is_tripped("stave-1") is True


@pytest.mark.asyncio
async def test_is_not_tripped():
    from datametronome_podium.core.circuit_breaker import StaveCircuitBreaker

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=b"2")
    cb = StaveCircuitBreaker(redis_client=mock_redis, threshold=5)

    assert await cb.is_tripped("stave-1") is False


@pytest.mark.asyncio
async def test_reset():
    from datametronome_podium.core.circuit_breaker import StaveCircuitBreaker

    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock()

    cb = StaveCircuitBreaker(redis_client=mock_redis, threshold=5, executor=mock_executor)

    await cb.reset("stave-1")
    mock_redis.delete.assert_awaited_once_with("circuit:stave-1:failures")
    mock_executor.execute.assert_awaited_once()
