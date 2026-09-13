"""Outbound alerting for failed checks.

A single webhook URL is read from app settings (`alert_webhook_url`). When it is
unset, alerting is simply off — which is the default for a fresh install.

The payload carries a top-level `text` field so a Slack incoming webhook renders
it without any Slack-specific code, plus the structured fields any other
consumer would want.

ponytail: one global webhook, fire-and-forget. Per-stave routing, retries and
dedupe belong in a real notification feature if this ever needs to page someone.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.settings.repo import AppSettingsRepo

logger = logging.getLogger(__name__)

# Statuses that are considered healthy — anything else alerts.
# Matches how the circuit breaker classifies a check result.
_OK_STATUSES = frozenset({"pass", "warn"})

_TIMEOUT_SECONDS = 10.0


async def notify_check_failure(
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
    """Post a failed check to the configured webhook.

    Never raises: a broken or slow webhook must not fail the check run that
    triggered it, and the result is already persisted by the time we get here.
    """
    if status in _OK_STATUSES:
        return

    try:
        webhook_url = await AppSettingsRepo(executor).get_decrypted("alert_webhook_url")
    except Exception:
        logger.warning("Could not read alert_webhook_url; skipping alert", exc_info=True)
        return

    if not webhook_url:
        return

    summary = f"[{severity}] {stave_name} / {clef_name}: {status}"
    payload: dict[str, Any] = {
        "text": f"{summary}\n{message or ''}".strip(),
        "check_id": check_id,
        "clef_id": clef_id,
        "clef_name": clef_name,
        "stave_id": stave_id,
        "stave_name": stave_name,
        "status": status,
        "severity": severity,
        "message": message,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
        logger.info("Alert sent for check %s (status=%s)", check_id, status)
    except Exception as exc:
        logger.error("Failed to send alert for check %s: %s", check_id, exc)
