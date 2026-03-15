"""Tests for ResultPusher."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_push_result_success():
    from datametronome_podium.tasks.result_pusher import ResultPusher

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    pusher = ResultPusher(central_api_url="https://central.example.com/api/v1")

    with patch("datametronome_podium.tasks.result_pusher.httpx.AsyncClient", return_value=mock_client):
        await pusher.push({"clef_id": "clef-1", "status": "pass"})

    mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_push_result_retry_on_failure():
    from datametronome_podium.tasks.result_pusher import ResultPusher
    import httpx

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectError("Connection refused")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    mock_client = AsyncMock()
    mock_client.post = mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    pusher = ResultPusher(
        central_api_url="https://central.example.com/api/v1",
        max_retries=3,
        retry_delay=0.01,
    )

    with patch("datametronome_podium.tasks.result_pusher.httpx.AsyncClient", return_value=mock_client):
        await pusher.push({"clef_id": "clef-1", "status": "pass"})

    assert call_count == 3


@pytest.mark.asyncio
async def test_push_result_raises_after_max_retries():
    from datametronome_podium.tasks.result_pusher import ResultPusher
    import httpx

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    pusher = ResultPusher(
        central_api_url="https://central.example.com/api/v1",
        max_retries=2,
        retry_delay=0.01,
    )

    with patch("datametronome_podium.tasks.result_pusher.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Failed to push"):
            await pusher.push({"clef_id": "clef-1", "status": "pass"})
