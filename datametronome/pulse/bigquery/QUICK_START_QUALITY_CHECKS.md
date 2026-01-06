# Quick Start: BigQuery Data Quality Checks

## ✅ Yes, you can create data quality checks on BigQuery!

BigQuery is fully integrated into DataMetronome. You can create and run data quality checks on any BigQuery tables.

## 🎯 Three Ways to Create Checks

### 1. Using YAML Configuration (Recommended)

Create a YAML file with your stave and clefs:

```yaml
staves:
  - id: stave-bigquery-001
    name: BigQuery Analytics
    data_source_type: bigquery
    connection_config:
      project_id: gen-lang-client-0489056598
      credentials_path: ${BIGQUERY_CREDENTIALS_PATH}
      dataset: bigquery-public-data.samples
      location: US
    is_active: true

clefs:
  - id: clef-rowcount-001
    stave_id: stave-bigquery-001
    name: Table Row Count Check
    check_type: row_count
    config:
      table: bigquery-public-data.samples.github_nested
      min_rows: 1
      max_rows: 1000000000
    schedule: "0 */6 * * *"
    is_active: true
```

Then import via API:
```bash
curl -X POST "http://localhost:8000/api/v1/config/import" \
  -H "Content-Type: application/json" \
  -d @your-config.yaml
```

### 2. Using REST API Directly

Create stave:
```bash
curl -X POST "http://localhost:8000/api/v1/staves" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BigQuery Analytics",
    "data_source_type": "bigquery",
    "connection_config": {
      "project_id": "gen-lang-client-0489056598",
      "credentials_path": "/path/to/credentials.json",
      "dataset": "bigquery-public-data.samples"
    }
  }'
```

Create clef:
```bash
curl -X POST "http://localhost:8000/api/v1/clefs" \
  -H "Content-Type: application/json" \
  -d '{
    "stave_id": "stave-bigquery-001",
    "name": "Row Count Check",
    "check_type": "row_count",
    "config": {
      "table": "bigquery-public-data.samples.github_nested",
      "min_rows": 1
    },
    "schedule": "0 */6 * * *"
  }'
```

### 3. Run Check Immediately

After creating a clef, you can run it immediately:

```bash
curl -X POST "http://localhost:8000/api/v1/clefs/{clef_id}/run-now" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📊 Supported Check Types

### Level 1 Checks (Available Now)

**row_count**: Check table has expected number of rows
```yaml
check_type: row_count
config:
  table: bigquery-public-data.samples.github_nested
  min_rows: 1000
  max_rows: 1000000
```

**freshness**: Check data is recent
```yaml
check_type: freshness
config:
  table: bigquery-public-data.samples.github_nested
  timestamp_column: repository_pushed_at
  max_age_hours: 24
```

**column_values**: Validate column values
```yaml
check_type: column_values
config:
  table: bigquery-public-data.samples.github_nested
  column: repository_language
  condition: if_not_in
  allowed_values: ["Python", "JavaScript", "Java"]
  threshold: 0.05
```

### Legacy Check Types (Also Supported)

- `null_check`: Check for NULL values
- `uniqueness_check`: Check for duplicates
- `range_check`: Check numeric ranges
- `pattern_check`: Check regex patterns

## 🔍 Example: Using Public Datasets

Since you can access `bigquery-public-data`, you can test with public datasets:

```yaml
staves:
  - id: stave-bq-public
    name: BigQuery Public Data
    data_source_type: bigquery
    connection_config:
      project_id: gen-lang-client-0489056598
      credentials_path: ${BIGQUERY_CREDENTIALS_PATH}
      dataset: bigquery-public-data.samples
    is_active: true

clefs:
  - stave_id: stave-bq-public
    name: GitHub Samples Row Count
    check_type: row_count
    config:
      table: bigquery-public-data.samples.github_nested
      min_rows: 1000
    schedule: "0 */6 * * *"
```

## 🚀 Next Steps

1. **Set up credentials**: Make sure `BIGQUERY_CREDENTIALS_PATH` points to your service account JSON
2. **Create a stave**: Define your BigQuery connection
3. **Create clefs**: Define your data quality checks
4. **Run checks**: Execute manually or let the scheduler run them automatically
5. **View results**: Check the dashboard or API for results

## 📚 More Information

- Full integration guide: `BIGQUERY_INTEGRATION.md`
- YAML examples: `example_bigquery_quality_check.yaml`
- API documentation: `datametronome/podium/API_IMPORT_GUIDE.md`
