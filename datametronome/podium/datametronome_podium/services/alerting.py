"""Outbound alerting for check results.

A single webhook URL is read from app settings (`alert_webhook_url`). When it
is unset, alerting is off -- the default for a fresh install.

The payload is one coloured Slack attachment carrying Block Kit blocks, with
`fallback` for notifications. There is no top-level `text`: Slack renders that
as the message body and the attachment underneath it, which printed every
headline twice. Non-Slack consumers read the structured fields alongside.

ponytail: one global webhook, fire-and-forget, one extra query per alert to
find the previous status. Per-stave routing, retries and dedupe belong in a
real notification feature if this ever needs to page someone.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import httpx

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.checks.model import SeverityLevel
from datametronome_podium.features.checks.repo import CheckRepo
from datametronome_podium.features.settings.repo import AppSettingsRepo

logger = logging.getLogger(__name__)

# Statuses that need no alert on their own. `warn` is here unless the operator
# opts in via the alert_on_warn setting.
_QUIET_STATUSES = frozenset({"pass"})

_TIMEOUT_SECONDS = 10.0

# Slack attachment colours by severity.
_COLOURS = {
    "fail": "#dc2626",
    "error": "#dc2626",
    "warn": "#f59e0b",
    "pass": "#16a34a",
}


async def notify_check_result(
    executor: QueryExecutor,
    *,
    check_id: str,
    clef_id: str,
    clef_name: str,
    stave_id: str,
    stave_name: str,
    status: str,
    message: str | None,
    severity: str,
) -> None:
    """Post a check result to the configured webhook, when it is worth posting.

    Never raises: a broken or slow webhook must not fail the check run that
    triggered it, and the result is already persisted by the time we get here.
    """
    try:
        settings = AppSettingsRepo(executor)
        webhook_url = await settings.get_decrypted("alert_webhook_url")
        if not webhook_url:
            return

        recovered = status == "pass" and await _was_failing(executor, clef_id)
        if not await _should_alert(settings, status, recovered):
            return

        base_url = await _plain(settings, "podium_base_url")
    except Exception:
        logger.warning("Could not read alerting settings; skipping", exc_info=True)
        return

    payload = build_payload(
        check_id=check_id,
        clef_id=clef_id,
        clef_name=clef_name,
        stave_id=stave_id,
        stave_name=stave_name,
        status=status,
        message=message,
        severity=severity,
        base_url=base_url,
        recovered=recovered,
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
        logger.info("Alert sent for check %s (status=%s)", check_id, status)
    except Exception as exc:
        logger.error("Failed to send alert for check %s: %s", check_id, exc)


async def _should_alert(settings: AppSettingsRepo, status: str, recovered: bool) -> bool:
    """A result is worth posting if it is bad, or if it just stopped being bad."""
    if recovered:
        return True
    if status in _QUIET_STATUSES:
        return False
    if status == "warn":
        return _truthy(await _plain(settings, "alert_on_warn"))
    return True


async def _was_failing(executor: QueryExecutor, clef_id: str) -> bool:
    """True when the check before this one was not passing.

    The current result is already written, so the previous one is index 1.
    A clef with no history has nothing to recover from.
    """
    try:
        recent = await CheckRepo(executor).list_by_clef(clef_id, limit=2)
    except Exception:
        logger.warning("Could not read check history for %s", clef_id, exc_info=True)
        return False
    return len(recent) > 1 and recent[1].status != "pass"


async def _plain(settings: AppSettingsRepo, key: str) -> str | None:
    """Read a non-sensitive setting's value. get() returns a row, not a string."""
    row = await settings.get(key)
    return row.value if row else None


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def build_payload(
    *,
    check_id: str,
    clef_id: str,
    clef_name: str,
    stave_id: str,
    stave_name: str,
    status: str,
    message: str | None,
    severity: str,
    base_url: str | None = None,
    recovered: bool = False,
) -> dict[str, Any]:
    """Build the Slack webhook body. Pure, so it is testable without a network."""
    # The colour stripe is invisible in a push notification; `text` is all the
    # phone gets. The icon is the only severity signal that reaches it.
    icon = _icon(SeverityLevel.HARMONY.value if recovered else severity)
    headline = (
        f"{icon} Recovered: {stave_name} / {clef_name}"
        if recovered
        else f"{icon} {stave_name} / {clef_name}: {status}"
    )
    detail = (message or "").strip()

    blocks: list[dict[str, Any]] = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{headline}*"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Stave*\n{stave_name}"},
                {"type": "mrkdwn", "text": f"*Check*\n{clef_name}"},
                {"type": "mrkdwn", "text": f"*Status*\n{status}"},
                {"type": "mrkdwn", "text": f"*Severity*\n{severity}"},
            ],
        },
    ]
    if detail:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": detail}}
        )

    link = _check_url(base_url, check_id)
    if link:
        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"<{link}|View check>"}],
            }
        )

    return {
        # No top-level `text`: Slack renders it as the message body *and* then
        # renders the attachment below, so the headline appeared twice. The
        # attachment's `fallback` is what notifications use instead.
        "attachments": [
            {
                "color": _COLOURS.get("pass" if recovered else status, "#6b7280"),
                "fallback": f"{headline}\n{detail}".strip(),
                "blocks": blocks,
            }
        ],
        # Structured fields for any consumer that is not Slack.
        "check_id": check_id,
        "clef_id": clef_id,
        "clef_name": clef_name,
        "stave_id": stave_id,
        "stave_name": stave_name,
        "status": status,
        "severity": severity,
        "message": message,
        "recovered": recovered,
    }


def _icon(severity: str) -> str:
    """Reuse the icons the severity enum already defines, not a second set."""
    try:
        return SeverityLevel(severity).icon
    except ValueError:
        return "❓"


def _check_url(base_url: str | None, check_id: str) -> str | None:
    """Deep link to this check, when a base URL is configured.

    Served by ui-nuxt/pages/checks/[id].vue, which reads the id from the route
    and fetches it via checksService.getById.
    """
    base = (base_url or "").strip()
    if not base:
        return None
    return urljoin(base.rstrip("/") + "/", f"checks/{check_id}")
