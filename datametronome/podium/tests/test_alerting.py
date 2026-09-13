"""Tests for check-failure webhook alerting."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from datametronome_podium.services.alerting import notify_check_failure

ARGS = {
    "check_id": "check-1",
    "clef_id": "clef-1",
    "clef_name": "row count",
    "stave_id": "stave-1",
    "stave_name": "orders",
    "message": "expected > 0, got 0",
    "severity": "critical",
}


def _executor():
    return MagicMock()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pass", "warn"])
async def test_healthy_statuses_do_not_alert(status):
    """A passing check must not read settings or hit the network."""
    with patch("datametronome_podium.services.alerting.AppSettingsRepo") as repo_cls:
        await notify_check_failure(_executor(), status=status, **ARGS)

    repo_cls.assert_not_called()


@pytest.mark.asyncio
async def test_no_webhook_configured_is_a_noop():
    """Alerting is off by default; absence of a URL must not error."""
    repo = MagicMock()
    repo.get_decrypted = AsyncMock(return_value=None)

    with patch("datametronome_podium.services.alerting.AppSettingsRepo", return_value=repo):
        with patch("httpx.AsyncClient") as client_cls:
            await notify_check_failure(_executor(), status="fail", **ARGS)

    client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_failure_posts_to_webhook():
    repo = MagicMock()
    repo.get_decrypted = AsyncMock(return_value="https://hooks.example.com/abc")

    post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
    client = MagicMock()
    client.post = post
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch("datametronome_podium.services.alerting.AppSettingsRepo", return_value=repo):
        with patch("httpx.AsyncClient", return_value=client):
            await notify_check_failure(_executor(), status="fail", **ARGS)

    post.assert_awaited_once()
    call = post.await_args
    assert call is not None
    assert call.args[0] == "https://hooks.example.com/abc"

    payload = call.kwargs["json"]
    assert payload["status"] == "fail"
    assert payload["check_id"] == "check-1"
    assert payload["severity"] == "critical"
    # Slack renders `text`; it must carry enough to be useful on its own.
    assert "orders" in payload["text"]
    assert "row count" in payload["text"]


@pytest.mark.asyncio
async def test_webhook_error_never_propagates():
    """A broken webhook must not fail the check run that triggered it."""
    repo = MagicMock()
    repo.get_decrypted = AsyncMock(return_value="https://hooks.example.com/abc")

    client = MagicMock()
    client.post = AsyncMock(side_effect=RuntimeError("connection refused"))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch("datametronome_podium.services.alerting.AppSettingsRepo", return_value=repo):
        with patch("httpx.AsyncClient", return_value=client):
            await notify_check_failure(_executor(), status="fail", **ARGS)
