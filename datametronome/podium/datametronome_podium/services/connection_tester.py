"""Connection Tester - checks that a stave's configuration actually connects.

One entry per data source in TESTERS at the bottom. There used to be an
if/elif chain here instead, and it had drifted out of step with what the
platform accepts: it still dispatched MySQL, Redis, MongoDB and HTTP, none of
which have a connector or pass stave validation, so those arms could not be
reached.

Every tester now takes its connector from the factory. Three of them used to
construct one by hand, which is how this path and the check path drifted apart
before: the factory learned to pass `ssl` through and the tester did not, so a
stave could pass its connection test and then fail every check.
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from datametronome_podium.core.connector_factory import create_connector
from datametronome_podium.features.staves.model import Stave

logger = logging.getLogger(__name__)


def _ok(message: str, **metadata: Any) -> dict[str, Any]:
    return {"success": True, "message": message, "metadata": metadata}


@asynccontextmanager
async def _connected(stave: Stave):
    """Yield a connected connector for the stave and always close it."""
    connector = await create_connector(
        stave.data_source_type or "", stave.connection_config or {}
    )
    try:
        yield connector
    finally:
        await connector.close()


async def get_connector(stave: Stave):
    """Return a connected connector. The caller closes it."""
    return await create_connector(
        stave.data_source_type or "", stave.connection_config or {}
    )


async def test_connection(stave: Stave) -> dict[str, Any]:
    """Test connection to a stave's data source.

    The testers below raise on failure rather than each formatting its own
    `{"success": False, ...}`; there were fourteen copies of that dict.
    """
    start_time = time.time()
    label = _LABELS.get(stave.data_source_type or "", stave.data_source_type)

    result: dict[str, Any]
    tester = TESTERS.get(stave.data_source_type or "")
    if tester is None:
        result = {
            "success": False,
            "message": f"Unsupported data source type: {stave.data_source_type}",
            "metadata": {},
        }
    else:
        try:
            result = await tester(stave)
        except ModuleNotFoundError as exc:
            result = {
                "success": False,
                "message": f"{label} support is not installed: {exc.name}",
                "metadata": {},
            }
        except KeyError as exc:
            result = {
                "success": False,
                "message": f"Missing required {label} configuration: {exc}",
                "metadata": {},
            }
        except Exception as exc:
            logger.error("Connection test failed for %s: %s", stave.name, exc)
            result = {
                "success": False,
                "message": f"{label} connection failed: {exc}",
                "metadata": {},
            }

    result["connection_time"] = time.time() - start_time
    return result


async def _test_postgres(stave: Stave) -> dict[str, Any]:
    config = stave.connection_config
    label = _LABELS[stave.data_source_type or "postgres"]
    default_port = 5439 if stave.data_source_type == "redshift" else 5432

    async with _connected(stave) as connector:
        version = await _scalar(connector, "SELECT version();", "version", "Unknown")
        schema_count = await _scalar(
            connector,
            "SELECT COUNT(*) as count FROM information_schema.schemata;",
            "count",
            0,
        )
        table_count = await _scalar(
            connector,
            "SELECT COUNT(*) as count FROM information_schema.tables;",
            "count",
            0,
        )
        return _ok(
            f"{label} connection successful",
            database_version=version,
            schema_count=schema_count,
            table_count=table_count,
            host=config["host"],
            port=config.get("port", default_port),
            database=config["database"],
        )


async def _test_s3(stave: Stave) -> dict[str, Any]:
    """Read every configured table rather than listing the bucket.

    Listing proves credentials and nothing else. Reading each table proves the
    path resolves, the format is what the extension claims, and the object is
    readable, which is what a check needs.
    """
    config = stave.connection_config

    async with _connected(stave) as connector:
        counts = {}
        for name in config.get("tables") or {}:
            rows = await connector.query(f'SELECT COUNT(*) AS n FROM "{name}"')
            counts[name] = rows[0]["n"] if rows else 0

        return _ok(
            f"S3 connection successful, {len(counts)} table(s) readable",
            bucket=config.get("bucket"),
            region=config.get("region", "us-east-1"),
            row_counts=counts,
            credentials=(
                "explicit keys"
                if config.get("access_key_id")
                else "instance role or environment"
            ),
        )


async def _test_sqlite(stave: Stave) -> dict[str, Any]:
    config = stave.connection_config
    db_path = config.get("database_path", config.get("path"))

    async with _connected(stave) as connector:
        version = await _scalar(
            connector, "SELECT sqlite_version() as version;", "version", "Unknown"
        )
        table_count = await _scalar(
            connector,
            "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table';",
            "count",
            0,
        )
        index_count = await _scalar(
            connector,
            "SELECT COUNT(*) as count FROM sqlite_master WHERE type='index';",
            "count",
            0,
        )
        return _ok(
            "SQLite connection successful",
            database_version=version,
            table_count=table_count,
            index_count=index_count,
            path=db_path,
            file_size_mb=round(_file_size_mb(db_path), 2),
        )


async def _test_bigquery(stave: Stave) -> dict[str, Any]:
    config = stave.connection_config
    project_id = config["project_id"]
    dataset = config.get("dataset")

    async with _connected(stave) as connector:
        if not await connector.is_connected():
            raise RuntimeError("connection established but health check failed")

        metadata: dict[str, Any] = {
            "project_id": project_id,
            "location": config.get("location", "US"),
        }
        if dataset:
            metadata["dataset"] = dataset
            metadata.update(await _bigquery_tables(connector, dataset, project_id))

        return {
            "success": True,
            "message": "BigQuery connection successful",
            "metadata": metadata,
        }


async def _bigquery_tables(connector, dataset: str, project_id: str) -> dict[str, Any]:
    """Count tables in the dataset, explaining the common misconfiguration.

    `bigquery-public-data` is a project, not a dataset, and people put it in
    the dataset field constantly.
    """
    out: dict[str, Any] = {}
    target = dataset
    if dataset == "bigquery-public-data":
        target = "bigquery-public-data.samples"
        out["note"] = (
            "'bigquery-public-data' is a project, not a dataset. Trying "
            "'bigquery-public-data.samples'. For others use "
            "'bigquery-public-data.DATASET_NAME'."
        )

    try:
        tables = await connector.list_tables(target)
        out["table_count"] = len(tables) if tables else 0
        if target != dataset:
            out["note"] = f"{out['note']} Found {out['table_count']} tables."
    except Exception as exc:
        logger.warning("Could not list tables for dataset %s: %s", dataset, exc)
        if ("404" in str(exc) or "Not found" in str(exc)) and "." not in dataset:
            out["note"] = (
                f"Dataset '{dataset}' not found in project '{project_id}'. If it "
                f"is public, use 'PROJECT.DATASET'. Connection succeeded; cannot "
                f"list tables."
            )
        else:
            out["note"] = f"Could not list tables: {exc}"
    return out


async def _test_dbt(stave: Stave) -> dict[str, Any]:
    config = stave.connection_config

    async with _connected(stave) as connector:
        models = await connector.query("models")
        sources = await connector.query("sources")
        tests = await connector.query("tests")
        return _ok(
            "dbt connection successful",
            mode=config.get("mode", "local"),
            model_count=len(models),
            source_count=len(sources),
            test_count=len(tests),
        )


async def _scalar(connector, sql: str, column: str, default: Any) -> Any:
    rows = await connector.query(sql)
    return rows[0][column] if rows else default


def _file_size_mb(file_path: str) -> float:
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return 0.0


_LABELS = {
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "redshift": "Redshift",
    "sqlite": "SQLite",
    "bigquery": "BigQuery",
    "s3": "S3",
    "dbt": "dbt",
}

# Keys must match features.staves.model.SUPPORTED_DATA_SOURCES.
# test_data_source_coverage.py asserts that, so a new stave type cannot ship
# with no way to test it.
TESTERS = {
    "postgres": _test_postgres,
    "postgresql": _test_postgres,
    "redshift": _test_postgres,
    "sqlite": _test_sqlite,
    "bigquery": _test_bigquery,
    "s3": _test_s3,
    "dbt": _test_dbt,
}
