"""End to end against a real DuckDB, with local files standing in for objects.

Only the S3 URI construction is substituted; test_paths.py covers that
directly. Everything else here is the real thing: view creation, the thread
hop, row mapping, and the guard on the live query path.
"""

import asyncio

import duckdb
import pytest

from metronome_pulse_s3 import S3ReadonlyPulse
from metronome_pulse_s3 import connector as connector_module


@pytest.fixture
def local_bucket(tmp_path, monkeypatch):
    """Write two files and make scan_expression point at them."""
    con = duckdb.connect(":memory:")
    users = tmp_path / "users.parquet"
    orders = tmp_path / "orders.csv"
    con.execute(
        f"COPY (SELECT * FROM (VALUES (1,'ada'),(2,'alan'),(3,'grace')) "
        f"t(id,name)) TO '{users}' (FORMAT parquet)"
    )
    orders.write_text("id,total\n1,10.5\n2,20.0\n")
    con.close()

    def fake_scan(bucket, path):
        assert bucket == "test-bucket"
        return f"'{tmp_path / path}'"

    monkeypatch.setattr(connector_module, "scan_expression", fake_scan)
    # No AWS call is made for local files, but connect() still issues the
    # secret statement, and credential_chain fails without an environment.
    monkeypatch.setattr(
        S3ReadonlyPulse, "_secret_sql", lambda self: "SELECT 1", raising=True
    )
    return tmp_path


@pytest.fixture
async def pulse(local_bucket):
    p = S3ReadonlyPulse(
        bucket="test-bucket",
        tables={"users": "users.parquet", "orders": "orders.csv"},
    )
    await p.connect()
    yield p
    await p.close()


@pytest.mark.asyncio
async def test_count_matches_the_file(pulse):
    rows = await pulse.query('SELECT COUNT(*) AS row_count FROM "users"')
    assert rows == [{"row_count": 3}]


@pytest.mark.asyncio
async def test_rows_come_back_as_dicts(pulse):
    rows = await pulse.query('SELECT id, name FROM "users" ORDER BY id')
    assert rows == [
        {"id": 1, "name": "ada"},
        {"id": 2, "name": "alan"},
        {"id": 3, "name": "grace"},
    ]


@pytest.mark.asyncio
async def test_csv_and_parquet_tables_coexist(pulse):
    rows = await pulse.query('SELECT COUNT(*) AS n FROM "orders"')
    assert rows == [{"n": 2}]


@pytest.mark.asyncio
async def test_the_check_layer_sql_shape_works(pulse):
    # The exact SQL clef_executor builds for a row_count check.
    rows = await pulse.query('SELECT COUNT(*) as row_count FROM "users"')
    assert rows[0]["row_count"] == 3


@pytest.mark.asyncio
async def test_parameterised_query(pulse):
    rows = await pulse.query(
        {"sql": 'SELECT name FROM "users" WHERE id = ?', "params": [2]}
    )
    assert rows == [{"name": "alan"}]


@pytest.mark.asyncio
async def test_writes_are_refused_on_the_live_connection(pulse, tmp_path):
    escape = tmp_path / "exfil.parquet"
    with pytest.raises(ValueError):
        await pulse.query(f"COPY \"users\" TO '{escape}' (FORMAT parquet)")
    assert not escape.exists()


@pytest.mark.asyncio
async def test_a_trailing_write_is_refused(pulse, tmp_path):
    escape = tmp_path / "exfil2.parquet"
    with pytest.raises(ValueError):
        await pulse.query(
            f"SELECT 1; COPY \"users\" TO '{escape}' (FORMAT parquet)"
        )
    assert not escape.exists()


@pytest.mark.asyncio
async def test_query_before_connect_raises():
    p = S3ReadonlyPulse(bucket="b", tables={"t": "t.parquet"})
    with pytest.raises(RuntimeError, match="Not connected"):
        await p.query("SELECT 1")


@pytest.mark.asyncio
async def test_close_is_idempotent(local_bucket):
    p = S3ReadonlyPulse(bucket="test-bucket", tables={"users": "users.parquet"})
    await p.connect()
    assert await p.is_connected()
    await p.close()
    await p.close()
    assert not await p.is_connected()


@pytest.mark.asyncio
async def test_missing_bucket_is_caught_before_duckdb():
    with pytest.raises(ValueError, match="bucket"):
        await S3ReadonlyPulse(tables={"t": "t.parquet"}).connect()


@pytest.mark.asyncio
async def test_missing_tables_is_caught_before_duckdb():
    with pytest.raises(ValueError, match="tables"):
        await S3ReadonlyPulse(bucket="b").connect()


@pytest.mark.asyncio
async def test_table_name_must_be_an_identifier(local_bucket):
    # The name is interpolated into CREATE VIEW, so it cannot be arbitrary.
    p = S3ReadonlyPulse(
        bucket="test-bucket", tables={'x" AS SELECT 1; --': "users.parquet"}
    )
    with pytest.raises(ValueError, match="Invalid table name"):
        await p.connect()


@pytest.mark.asyncio
async def test_concurrent_queries_are_serialised(pulse):
    results = await asyncio.gather(
        *(pulse.query('SELECT COUNT(*) AS n FROM "users"') for _ in range(8))
    )
    assert all(r == [{"n": 3}] for r in results)


def test_explicit_keys_build_a_secret():
    p = S3ReadonlyPulse(
        bucket="b",
        region="eu-west-1",
        access_key_id="AKIA_EXAMPLE",
        secret_access_key="shhh",
        session_token="tok",
    )
    sql = p._secret_sql()
    assert "KEY_ID 'AKIA_EXAMPLE'" in sql
    assert "SECRET 'shhh'" in sql
    assert "SESSION_TOKEN 'tok'" in sql
    assert "REGION 'eu-west-1'" in sql
    assert "credential_chain" not in sql


def test_no_keys_falls_back_to_the_instance_role():
    sql = S3ReadonlyPulse(bucket="b")._secret_sql()
    assert "PROVIDER credential_chain" in sql
    assert "KEY_ID" not in sql


def test_http_endpoint_disables_tls():
    # MinIO in a compose network is plain HTTP.
    sql = S3ReadonlyPulse(bucket="b", endpoint_url="http://minio:9000")._secret_sql()
    assert "ENDPOINT 'minio:9000'" in sql
    assert "USE_SSL false" in sql


def test_https_endpoint_keeps_tls():
    sql = S3ReadonlyPulse(bucket="b", endpoint_url="https://s3.example.com")._secret_sql()
    assert "ENDPOINT 's3.example.com'" in sql
    assert "USE_SSL" not in sql


def test_a_custom_endpoint_uses_path_addressing():
    # DuckDB defaults to bucket.host, which MinIO does not answer.
    assert "URL_STYLE 'path'" in (
        S3ReadonlyPulse(bucket="b", endpoint_url="http://minio:9000")._secret_sql()
    )


def test_real_aws_keeps_the_default_addressing():
    assert "URL_STYLE" not in S3ReadonlyPulse(bucket="b")._secret_sql()
