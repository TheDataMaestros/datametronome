# metronome-pulse-s3

Read-only DataPulse connector for files in S3. Parquet, CSV and JSON objects
become SQL tables, so every quality check that runs against a database runs
against a bucket unchanged.

DuckDB's `httpfs` extension does the reading. S3 has no query engine of its
own, and this avoids adding a second SQL generator to the check layer.

## Install

```bash
pip install metronome-pulse-s3
```

## Use

```python
from metronome_pulse_s3 import S3ReadonlyPulse

pulse = S3ReadonlyPulse(
    bucket="analytics-prod",
    region="eu-west-1",
    tables={
        "users": "users/*.parquet",
        "orders": "orders/dt=*/*.parquet",
        "signups": "raw/signups.csv.gz",
    },
)

await pulse.connect()
rows = await pulse.query('SELECT COUNT(*) AS n FROM "users"')
await pulse.close()
```

Each key in `tables` becomes a view. The value is a path inside the bucket, or
a full `s3://` URI to read from a different bucket.

The reader is chosen by extension, after stripping `.gz`, `.zst`, `.bz2` and
`.br`: `.parquet` and `.pq` use `read_parquet`, `.csv`/`.tsv`/`.txt` use
`read_csv_auto`, `.json`/`.ndjson`/`.jsonl` use `read_json_auto`. Anything
else is read as Parquet.

## Credentials

Pass `access_key_id` and `secret_access_key` (and `session_token` for
temporary credentials) to use explicit keys.

Leave them out and DuckDB's `credential_chain` provider takes over, which
picks up an ECS task role, an EKS service account, an EC2 instance profile or
the usual `AWS_*` environment variables. Prefer this in a deployed
environment: no long-lived key ends up in the stave config.

`endpoint_url` points the connector at MinIO or another S3-compatible store.
An `http://` endpoint turns off TLS.

## Read-only

There is no write method, and `query()` rejects anything that is not a single
`SELECT`, `WITH`, `DESCRIBE`, `EXPLAIN` or `SUMMARIZE`. Both rules are needed:
DuckDB runs every statement in a string it is given, so a verb check alone
would let `SELECT 1; COPY t TO 's3://...'` through.

Statement splitting understands string literals, so `WHERE action = 'delete'`
and a path containing a semicolon are not mistaken for a second statement.

## Limits

One DuckDB connection per connector, behind a lock, so checks against the same
stave run one at a time.
