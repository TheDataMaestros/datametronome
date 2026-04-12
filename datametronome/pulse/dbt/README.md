# metronome-pulse-dbt

Read-only dbt artifact connector for DataMetronome. Exposes dbt project metadata
(manifest, run results, catalog) as virtual queryable tables via the Pulse connector
interface.

## Installation

```bash
pip install metronome-pulse-dbt
```

## Configuration

### Local Mode

Reads dbt artifacts from the filesystem (`target/` directory):

```json
{
  "mode": "local",
  "project_path": "/path/to/dbt/project",
  "target_path": "target"
}
```

`target_path` defaults to `"target"`. The connector reads:
- `manifest.json` (required)
- `run_results.json` (optional)
- `catalog.json` (optional — run `dbt docs generate` to produce this)

### Cloud Mode

Fetches artifacts from the dbt Cloud API:

```json
{
  "mode": "cloud",
  "api_token": "your-dbt-cloud-token",
  "account_id": "12345",
  "job_id": "67890"
}
```

The connector finds the latest completed run for the given job and fetches its artifacts.

## Virtual Tables

The connector exposes dbt metadata as queryable virtual tables:

| Table | Source Artifact | Key Columns |
|---|---|---|
| `models` | manifest.json | unique_id, name, schema, database, materialization, tags, description, depends_on, path |
| `sources` | manifest.json | unique_id, name, source_name, schema, database, identifier, freshness_warn_after, freshness_error_after |
| `tests` | manifest.json | unique_id, name, test_type, model, column_name, severity, tags |
| `test_results` | run_results.json | unique_id, status, execution_time, message, failures, timestamp |
| `columns` | catalog.json | model_unique_id, model_name, column_name, column_type, description |
| `exposures` | manifest.json | unique_id, name, type, owner, depends_on |

## Querying

### By table name

```python
rows = await connector.query("models")
```

### With filters

```python
rows = await connector.query({
    "table": "models",
    "where": {"materialization": "table"},
    "columns": ["name", "schema"],
    "order_by": "name",
    "limit": 10,
})
```

### Where clause

- **Equality**: `{"materialization": "table"}` — matches rows where the field equals the value
- **List containment**: `{"tags": "finance"}` — matches rows where the value is in the list field

### Ordering

- Ascending: `"order_by": "name"`
- Descending: `"order_by": "-name"`

## Introspection

- `list_tables()` — returns dbt model names (not virtual table names)
- `get_table_info(model_name)` — returns column info from catalog for the given model

## Usage with DataMetronome

Create a stave with `data_source_type: "dbt"`:

```bash
curl -X POST http://localhost:8001/api/v1/staves \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My dbt Project",
    "data_source_type": "dbt",
    "connection_config": {
      "mode": "local",
      "project_path": "/path/to/dbt/project"
    }
  }'
```

Then test the connection and list tables as usual via the stave action endpoints.

## Limitations

- **Read-only**: write, execute, and transaction methods raise `NotImplementedError`
- **Metadata only**: queries return dbt metadata, not warehouse data
- **No SQL**: SQL strings are rejected with a helpful error; use table names or query dicts
