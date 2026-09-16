"""Against a real S3 API.

The other tests substitute local paths for S3 URIs, which leaves the parts most
likely to be wrong untested: whether httpfs installs and loads, whether the
CREATE SECRET syntax is the one this DuckDB accepts, and whether an s3:// URI
resolves at all. Those only fail when a bucket is on the other end.

Skipped unless S3_TEST_ENDPOINT is set. CI sets it and runs MinIO; see the
"Start MinIO" step in the workflow.
"""

import os

import duckdb
import pytest

from metronome_pulse_s3 import S3ReadonlyPulse

ENDPOINT = os.environ.get("S3_TEST_ENDPOINT", "")
BUCKET = os.environ.get("S3_TEST_BUCKET", "test-bucket")
KEY_ID = os.environ.get("S3_TEST_KEY_ID", "minioadmin")
SECRET = os.environ.get("S3_TEST_SECRET", "minioadmin")

pytestmark = pytest.mark.skipif(
    not ENDPOINT, reason="S3_TEST_ENDPOINT not set; no S3-compatible endpoint"
)


def _write_fixture(name: str, select: str) -> None:
    """Put an object in the bucket using DuckDB's own S3 writer."""
    con = duckdb.connect(":memory:")
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    con.execute(
        f"""
        CREATE OR REPLACE SECRET writer (
            TYPE s3, REGION 'us-east-1',
            KEY_ID '{KEY_ID}', SECRET '{SECRET}',
            ENDPOINT '{ENDPOINT.split("://", 1)[-1]}',
            USE_SSL {"true" if ENDPOINT.startswith("https") else "false"},
            URL_STYLE 'path'
        )
        """
    )
    con.execute(f"COPY ({select}) TO 's3://{BUCKET}/{name}' (FORMAT parquet)")
    con.close()


def _ensure_bucket() -> None:
    """Create the bucket if it is not already there.

    boto3 is a test-only dependency. The connector never uses it: DuckDB's
    httpfs speaks S3 directly, which is why it is not in the package deps.
    """
    boto3 = pytest.importorskip("boto3", reason="boto3 needed to seed the bucket")

    client = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=KEY_ID,
        aws_secret_access_key=SECRET,
        region_name="us-east-1",
    )
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    if BUCKET not in existing:
        client.create_bucket(Bucket=BUCKET)


@pytest.fixture(scope="module")
def seeded():
    _ensure_bucket()
    _write_fixture(
        "users/part-0.parquet",
        "SELECT * FROM (VALUES (1,'ada'),(2,'alan'),(3,'grace')) t(id,name)",
    )
    _write_fixture(
        "users/part-1.parquet",
        "SELECT * FROM (VALUES (4,'katherine')) t(id,name)",
    )
    return True


@pytest.fixture
async def pulse(seeded):
    p = S3ReadonlyPulse(
        bucket=BUCKET,
        tables={"users": "users/*.parquet"},
        region="us-east-1",
        access_key_id=KEY_ID,
        secret_access_key=SECRET,
        endpoint_url=ENDPOINT,
    )
    await p.connect()
    yield p
    await p.close()


@pytest.mark.asyncio
async def test_httpfs_loads_and_the_uri_resolves(pulse):
    rows = await pulse.query('SELECT COUNT(*) AS row_count FROM "users"')
    # Both objects behind the glob, not just the first.
    assert rows == [{"row_count": 4}]


@pytest.mark.asyncio
async def test_rows_read_back_intact(pulse):
    rows = await pulse.query('SELECT id, name FROM "users" ORDER BY id')
    assert [r["name"] for r in rows] == ["ada", "alan", "grace", "katherine"]


@pytest.mark.asyncio
async def test_the_secret_statement_is_accepted_as_written(seeded):
    # connect() issues CREATE SECRET, so reaching a successful query proves
    # this DuckDB accepted the syntax and the credentials authenticated.
    p = S3ReadonlyPulse(
        bucket=BUCKET,
        tables={"users": "users/*.parquet"},
        access_key_id=KEY_ID,
        secret_access_key=SECRET,
        endpoint_url=ENDPOINT,
    )
    await p.connect()
    try:
        assert await p.is_connected()
    finally:
        await p.close()


@pytest.mark.asyncio
async def test_a_bad_path_fails_at_connect_not_at_check_time(seeded):
    p = S3ReadonlyPulse(
        bucket=BUCKET,
        tables={"missing": "nothing/here/*.parquet"},
        access_key_id=KEY_ID,
        secret_access_key=SECRET,
        endpoint_url=ENDPOINT,
    )
    with pytest.raises(Exception):
        await p.connect()
    await p.close()


@pytest.mark.asyncio
async def test_writes_are_refused_against_a_real_bucket(pulse):
    # The guard is what stops a check from exporting a table to object storage.
    with pytest.raises(ValueError):
        await pulse.query(
            f"COPY \"users\" TO 's3://{BUCKET}/exfil.parquet' (FORMAT parquet)"
        )
