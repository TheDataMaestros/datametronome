"""
ResultPusher — pushes check results to a central API (hybrid mode).

Used by RemoteDispatcher when the agent runs checks locally
and needs to report results to the central DataMetronome platform.
"""
import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ResultPusher:
    """Push check results to a central API via HTTPS."""

    def __init__(
        self,
        central_api_url: str,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        api_key: str | None = None,
    ) -> None:
        self._url = f"{central_api_url.rstrip('/')}/checks/results"
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._api_key = api_key

    async def push(self, result: dict[str, Any]) -> None:
        """Push a check result to the central API with retry."""
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        last_error: Exception | None = None

        async with httpx.AsyncClient() as client:
            for attempt in range(1, self._max_retries + 1):
                try:
                    response = await client.post(
                        self._url,
                        json=result,
                        headers=headers,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    logger.info("Result pushed to central API: clef=%s", result.get("clef_id"))
                    return
                except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                    last_error = e
                    logger.warning(
                        "Push attempt %d/%d failed: %s",
                        attempt, self._max_retries, e,
                    )
                    if attempt < self._max_retries:
                        await asyncio.sleep(self._retry_delay * attempt)

        logger.error("Failed to push result after %d attempts: %s", self._max_retries, last_error)
        raise RuntimeError(
            f"Failed to push result to central API after {self._max_retries} attempts"
        ) from last_error
