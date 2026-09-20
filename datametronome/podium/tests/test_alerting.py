"""Tests for check-result webhook alerting."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from datametronome_podium.services.alerting import build_payload, notify_check_result

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


def _settings(webhook="https://hooks.example.com/abc", **plain):
    """AppSettingsRepo double. `plain` holds non-sensitive key -> value."""
    repo = MagicMock()
    repo.get_decrypted = AsyncMock(return_value=webhook)
    repo.get = AsyncMock(
        side_effect=lambda key: MagicMock(value=plain[key]) if key in plain else None
    )
    return repo


def _client():
    client = MagicMock()
    client.post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def _history(*statuses):
    """CheckRepo double returning the given statuses newest-first."""
    repo = MagicMock()
    repo.list_by_clef = AsyncMock(
        return_value=[MagicMock(status=s) for s in statuses]
    )
    return repo


async def _run(status, *, settings=None, history=("fail", "fail")):
    client = _client()
    with patch("datametronome_podium.services.alerting.AppSettingsRepo",
               return_value=settings or _settings()), \
         patch("datametronome_podium.services.alerting.CheckRepo",
               return_value=_history(*history)), \
         patch("httpx.AsyncClient", return_value=client):
        await notify_check_result(_executor(), status=status, **ARGS)
    return client


# --- when we post at all ----------------------------------------------------


@pytest.mark.asyncio
async def test_no_webhook_configured_is_a_noop():
    """Alerting is off by default; absence of a URL must not error."""
    with patch("datametronome_podium.services.alerting.AppSettingsRepo",
               return_value=_settings(webhook=None)), \
         patch("httpx.AsyncClient") as client_cls:
        await notify_check_result(_executor(), status="fail", **ARGS)

    client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_a_passing_check_after_a_pass_is_silent():
    """Steady green must not chat. This is most check runs."""
    client = await _run("pass", history=("pass", "pass"))
    client.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_failure_posts():
    client = await _run("fail")
    client.post.assert_awaited_once()
    assert client.post.await_args.args[0] == "https://hooks.example.com/abc"


@pytest.mark.asyncio
async def test_warn_is_silent_unless_opted_in():
    client = await _run("warn")
    client.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_warn_posts_when_alert_on_warn_is_set():
    client = await _run("warn", settings=_settings(alert_on_warn="true"))
    client.post.assert_awaited_once()


@pytest.mark.parametrize("value,expected", [
    ("true", True), ("True", True), ("1", True), ("yes", True), ("on", True),
    ("false", False), ("0", False), ("", False), ("nonsense", False),
])
@pytest.mark.asyncio
async def test_alert_on_warn_accepts_the_usual_spellings(value, expected):
    client = await _run("warn", settings=_settings(alert_on_warn=value))
    assert (client.post.await_count == 1) is expected


# --- recovery ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_pass_after_a_failure_posts_a_recovery():
    # Newest-first: [this pass, the previous fail].
    client = await _run("pass", history=("pass", "fail"))
    client.post.assert_awaited_once()
    payload = client.post.await_args.kwargs["json"]
    assert payload["recovered"] is True
    assert "Recovered" in payload["text"]


@pytest.mark.asyncio
async def test_a_first_ever_pass_is_not_a_recovery():
    """No history means nothing to recover from."""
    client = await _run("pass", history=("pass",))
    client.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_unreadable_history_does_not_invent_a_recovery():
    repo = MagicMock()
    repo.list_by_clef = AsyncMock(side_effect=RuntimeError("db gone"))
    client = _client()
    with patch("datametronome_podium.services.alerting.AppSettingsRepo",
               return_value=_settings()), \
         patch("datametronome_podium.services.alerting.CheckRepo", return_value=repo), \
         patch("httpx.AsyncClient", return_value=client):
        await notify_check_result(_executor(), status="pass", **ARGS)

    client.post.assert_not_awaited()


# --- payload shape ----------------------------------------------------------


def test_payload_carries_a_text_fallback():
    """Slack uses `text` for push notifications and warns when it is absent."""
    payload = build_payload(status="fail", recovered=False, **ARGS)
    assert "orders" in payload["text"]
    assert "row count" in payload["text"]


def test_payload_is_one_coloured_attachment_of_blocks():
    payload = build_payload(status="fail", recovered=False, **ARGS)
    (attachment,) = payload["attachments"]
    assert attachment["color"] == "#dc2626"
    assert all("type" in b for b in attachment["blocks"])


def test_a_recovery_is_green_whatever_the_status_colour_would_be():
    payload = build_payload(status="pass", recovered=True, **ARGS)
    assert payload["attachments"][0]["color"] == "#16a34a"


def test_no_base_url_means_no_link_block():
    payload = build_payload(status="fail", recovered=False, **ARGS)
    rendered = str(payload["attachments"][0]["blocks"])
    assert "View check" not in rendered


@pytest.mark.parametrize("base", ["https://dm.example.com", "https://dm.example.com/"])
def test_a_base_url_adds_a_link_to_the_check(base):
    """Trailing slash or not, the URL must come out the same."""
    payload = build_payload(status="fail", recovered=False, base_url=base, **ARGS)
    link = payload["attachments"][0]["blocks"][-1]["elements"][0]["text"]
    assert link == "<https://dm.example.com/checks/check-1|View check>"


def test_an_empty_message_does_not_add_an_empty_block():
    payload = build_payload(
        status="fail", recovered=False, **{**ARGS, "message": "   "}
    )
    assert "" not in [
        b.get("text", {}).get("text") for b in payload["attachments"][0]["blocks"]
    ]


# --- failure isolation ------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_error_never_propagates():
    """A broken webhook must not fail the check run that triggered it."""
    client = MagicMock()
    client.post = AsyncMock(side_effect=RuntimeError("connection refused"))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch("datametronome_podium.services.alerting.AppSettingsRepo",
               return_value=_settings()), \
         patch("datametronome_podium.services.alerting.CheckRepo",
               return_value=_history("fail", "fail")), \
         patch("httpx.AsyncClient", return_value=client):
        await notify_check_result(_executor(), status="fail", **ARGS)


@pytest.mark.asyncio
async def test_unreadable_settings_never_propagate():
    repo = MagicMock()
    repo.get_decrypted = AsyncMock(side_effect=RuntimeError("db gone"))
    with patch("datametronome_podium.services.alerting.AppSettingsRepo", return_value=repo), \
         patch("httpx.AsyncClient") as client_cls:
        await notify_check_result(_executor(), status="fail", **ARGS)

    client_cls.assert_not_called()
