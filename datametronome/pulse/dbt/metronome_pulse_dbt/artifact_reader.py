"""Artifact reader implementations for dbt local projects and dbt Cloud."""

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

from .exceptions import ArtifactNotFoundError, ArtifactParseError, CloudApiError


class ArtifactReader(ABC):
    """Abstract base for reading dbt JSON artifacts."""

    @abstractmethod
    async def read_manifest(self) -> dict[str, Any]:
        """Return parsed manifest.json contents.

        Raises ArtifactNotFoundError if the artifact is missing — manifest is
        mandatory for any dbt project introspection.
        """
        ...

    @abstractmethod
    async def read_run_results(self) -> dict[str, Any] | None:
        """Return parsed run_results.json, or None if not available.

        run_results is produced only after a dbt run/test, so its absence is
        normal and callers must handle None.
        """
        ...

    @abstractmethod
    async def read_catalog(self) -> dict[str, Any] | None:
        """Return parsed catalog.json, or None if not available.

        catalog.json is produced only after `dbt docs generate`, so callers
        must handle None.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Return True if the artifact source is accessible (manifest present)."""
        ...


# ---------------------------------------------------------------------------
# Local filesystem reader
# ---------------------------------------------------------------------------


def _read_json_sync(path: Path) -> dict[str, Any]:
    """Blocking JSON read — run inside an executor to stay off the event loop."""
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ArtifactParseError(f"Invalid JSON in {path}: {exc}") from exc


class LocalArtifactReader(ArtifactReader):
    """Read dbt artifacts from a local filesystem target directory."""

    def __init__(self, project_path: str, target_path: str = "target") -> None:
        self._target_dir = Path(project_path) / target_path

    def _artifact_path(self, filename: str) -> Path:
        return self._target_dir / filename

    async def _read_file(self, path: Path) -> dict[str, Any]:
        """Offload blocking file I/O to a thread so the event loop stays free."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _read_json_sync, path)

    async def read_manifest(self) -> dict[str, Any]:
        path = self._artifact_path("manifest.json")
        if not path.exists():
            raise ArtifactNotFoundError(f"manifest.json not found at {path}")
        return await self._read_file(path)

    async def read_run_results(self) -> dict[str, Any] | None:
        path = self._artifact_path("run_results.json")
        if not path.exists():
            return None
        return await self._read_file(path)

    async def read_catalog(self) -> dict[str, Any] | None:
        path = self._artifact_path("catalog.json")
        if not path.exists():
            return None
        return await self._read_file(path)

    async def is_available(self) -> bool:
        return self._artifact_path("manifest.json").exists()


# ---------------------------------------------------------------------------
# dbt Cloud API reader
# ---------------------------------------------------------------------------


class CloudArtifactReader(ArtifactReader):
    """Read dbt artifacts from the dbt Cloud API.

    Fetches artifacts from the most recently finished run for a given job.
    Auth uses a token header — dbt Cloud does not support basic auth for the
    v2 API.
    """

    def __init__(
        self,
        api_token: str,
        account_id: str,
        job_id: str,
        base_url: str = "https://cloud.getdbt.com/api/v2",
    ) -> None:
        self._api_token = api_token
        self._account_id = account_id
        self._job_id = job_id
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Token {api_token}"}

    async def _get_latest_run_id(self) -> str:
        """Fetch the most recently finished run ID for the configured job."""
        url = (
            f"{self._base_url}/accounts/{self._account_id}/runs/"
            f"?job_definition_id={self._job_id}&order_by=-finished_at&limit=1"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers)
        self._raise_for_auth(response)
        response.raise_for_status()
        data = response.json()
        return str(data["data"][0]["id"])

    async def _fetch_artifact(self, filename: str) -> dict[str, Any] | None:
        """Fetch a single artifact by filename from the latest run.

        Returns None for 404 (artifact not generated for this run).
        Raises CloudApiError on auth errors; raises httpx errors for other
        non-200 responses.
        """
        run_id = await self._get_latest_run_id()
        url = (
            f"{self._base_url}/accounts/{self._account_id}"
            f"/runs/{run_id}/artifacts/{filename}"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers)
        self._raise_for_auth(response)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        try:
            return response.json()
        except Exception as exc:
            raise ArtifactParseError(
                f"Failed to parse {filename} from dbt Cloud response"
            ) from exc

    def _raise_for_auth(self, response: httpx.Response) -> None:
        """Convert 401/403 responses to CloudApiError with the status code."""
        if response.status_code in (401, 403):
            raise CloudApiError(
                f"dbt Cloud auth failed ({response.status_code})",
                status_code=response.status_code,
            )

    async def read_manifest(self) -> dict[str, Any]:
        result = await self._fetch_artifact("manifest.json")
        if result is None:
            raise ArtifactNotFoundError("manifest.json not found in dbt Cloud run")
        return result

    async def read_run_results(self) -> dict[str, Any] | None:
        return await self._fetch_artifact("run_results.json")

    async def read_catalog(self) -> dict[str, Any] | None:
        return await self._fetch_artifact("catalog.json")

    async def is_available(self) -> bool:
        """Return True if the runs list endpoint responds successfully."""
        url = (
            f"{self._base_url}/accounts/{self._account_id}/runs/"
            f"?job_definition_id={self._job_id}&order_by=-finished_at&limit=1"
        )
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self._headers)
            return response.status_code == 200
        except httpx.HTTPError:
            return False
