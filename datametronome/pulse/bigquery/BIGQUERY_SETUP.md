# BigQuery DataPulse Setup Guide

Complete guide for setting up and using BigQuery with DataMetronome.

## 📋 Prerequisites

### 1. Google Cloud Platform Setup

1. **Create a GCP Project** (if you don't have one)
   ```bash
   gcloud projects create my-datametronome-project
   gcloud config set project my-datametronome-project
   ```

2. **Enable BigQuery API**
   ```bash
   gcloud services enable bigquery.googleapis.com
   ```

3. **Create a Service Account**
   ```bash
   gcloud iam service-accounts create datametronome-sa \
       --display-name="DataMetronome Service Account"
   ```

4. **Grant BigQuery Permissions**

   For **read-only** access (data quality checks):
   ```bash
   gcloud projects add-iam-policy-binding my-gcp-project \
       --member="serviceAccount:datametronome-sa@my-gcp-project.iam.gserviceaccount.com" \
       --role="roles/bigquery.dataViewer"

   gcloud projects add-iam-policy-binding my-gcp-project \
       --member="serviceAccount:datametronome-sa@my-gcp-project.iam.gserviceaccount.com" \
       --role="roles/bigquery.jobUser"
   ```

   For **read-write** access (data generation and writes):
   ```bash
   gcloud projects add-iam-policy-binding my-gcp-project \
       --member="serviceAccount:datametronome-sa@my-gcp-project.iam.gserviceaccount.com" \
       --role="roles/bigquery.dataEditor"

   gcloud projects add-iam-policy-binding my-gcp-project \
       --member="serviceAccount:datametronome-sa@my-gcp-project.iam.gserviceaccount.com" \
       --role="roles/bigquery.jobUser"
   ```

5. **Download Credentials**
   ```bash
   gcloud iam service-accounts keys create ~/bigquery-credentials.json \
       --iam-account=datametronome-sa@my-gcp-project.iam.gserviceaccount.com
   ```

### 2. Install BigQuery DataPulse

```bash
# Install from source (development)
cd datametronome/pulse/bigquery
pip install -e .

# Or install from PyPI (when published)
pip install metronome-pulse-bigquery
```

## 🚀 Quick Start

### Method 1: Python API

```python
import asyncio
from metronome_pulse_bigquery import BigQueryPulse

async def main():
    # Initialize connector
    pulse = BigQueryPulse(
        project_id="my-gcp-project",
        credentials_path="/path/to/bigquery-credentials.json",
        dataset="analytics"
    )

    # Connect
    await pulse.connect()

    # Query data
    results = await pulse.query("SELECT * FROM users LIMIT 10")
    print(f"Found {len(results)} users")

    # Write data
    data = [
        {"user_id": 1, "name": "Alice", "email": "alice@example.com"},
        {"user_id": 2, "name": "Bob", "email": "bob@example.com"}
    ]
    await pulse.write(data, "users")

    # Close connection
    await pulse.close()

asyncio.run(main())
```

### Method 2: YAML Configuration

Create a stave configuration file:

```yaml
# bigquery-stave.yaml
staves:
  - id: stave-bigquery-001
    name: My BigQuery Analytics
    description: Production BigQuery database
    data_source_type: bigquery
    connection_config:
      project_id: my-gcp-project
      credentials_path: /path/to/bigquery-credentials.json
      dataset: analytics
      location: US
    is_active: true

clefs:
  - id: clef-null-check-001
    name: Email NULL Check
    stave_id: stave-bigquery-001
    check_type: null_check
    config:
      table: users
      column: email
      threshold: 0.0
    schedule: "0 */6 * * *"
    is_active: true
```

Import the configuration:

```bash
cd datametronome/podium
python scripts/import_yaml.py --file bigquery-stave.yaml
```

### Method 3: REST API

1. **Create a Stave**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/staves" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "BigQuery Analytics",
       "description": "Production BigQuery database",
       "data_source_type": "bigquery",
       "connection_config": {
         "project_id": "my-gcp-project",
         "credentials_path": "/path/to/credentials.json",
         "dataset": "analytics",
         "location": "US"
       },
       "is_active": true
     }'
   ```

2. **Create a Clef (Data Quality Check)**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/clefs" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Email NULL Check",
       "stave_id": "stave-bigquery-001",
       "check_type": "null_check",
       "config": {
         "table": "users",
         "column": "email",
         "threshold": 0.0
       },
       "schedule": "0 */6 * * *",
       "is_active": true
     }'
   ```

## 🔧 Configuration Options

### Connection Configuration

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `project_id` | Yes | - | GCP project ID |
| `credentials_path` | Yes* | - | Path to service account JSON file |
| `credentials_json` | Yes* | - | Service account credentials as dict |
| `dataset` | No | - | Default dataset name |
| `location` | No | `US` | BigQuery location (US, EU, etc.) |

*Either `credentials_path` or `credentials_json` must be provided.

### Using Environment Variables

For security, use environment variables:

```yaml
connection_config:
  project_id: ${BIGQUERY_PROJECT_ID}
  credentials_path: ${BIGQUERY_CREDENTIALS_PATH}
  dataset: ${BIGQUERY_DATASET}
```

Then set:
```bash
export BIGQUERY_PROJECT_ID=my-gcp-project
export BIGQUERY_CREDENTIALS_PATH=/secure/path/to/credentials.json
export BIGQUERY_DATASET=analytics
```

### Using Credentials JSON Directly

```python
credentials_json = {
    "type": "service_account",
    "project_id": "my-gcp-project",
    "private_key_id": "...",
    "private_key": "...",
    "client_email": "...",
    "client_id": "...",
    # ... other fields
}

pulse = BigQueryPulse(
    project_id="my-gcp-project",
    credentials_json=credentials_json,
    dataset="analytics"
)
```

## 📊 Supported Check Types

### 1. NULL Check
Validates that columns don't contain NULL values.

```yaml
check_type: null_check
config:
  table: users
  column: email
  threshold: 0.0  # 0% nulls allowed
```

### 2. Row Count Check
Ensures tables have expected number of rows.

```yaml
check_type: row_count
config:
  table: events
  min_rows: 1000
  max_rows: 1000000000
```

### 3. Uniqueness Check
Verifies columns have no duplicates.

```yaml
check_type: uniqueness
config:
  table: users
  column: user_id
  threshold: 0.0  # 0% duplicates
```

### 4. Range Check
Validates numeric values are within range.

```yaml
check_type: range_check
config:
  table: orders
  column: amount
  min_value: 0
  max_value: 100000
  threshold: 0.01  # 1% allowed out of range
```

### 5. Pattern Check
Validates string patterns using regex.

```yaml
check_type: pattern_check
config:
  table: users
  column: email
  pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
  threshold: 0.02  # 2% allowed to not match
```

**Note**: BigQuery uses `REGEXP_CONTAINS()` for pattern matching.

### 6. Freshness Check
Ensures data is recent.

```yaml
check_type: freshness
config:
  table: events
  timestamp_column: created_at
  max_age_hours: 24
```

### 7. Column Values Check
Validates values are in allowed set.

```yaml
check_type: column_values
config:
  table: orders
  column: status
  allowed_values:
    - pending
    - completed
    - cancelled
  threshold: 0.0
```

### 8. Custom SQL Check (Advanced)
Execute custom SQL queries.

```yaml
check_type: custom_sql
config:
  sql: |
    SELECT
      DATE(created_at) as date,
      SUM(amount) as daily_revenue
    FROM orders
    WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY DATE(created_at)
    HAVING SUM(amount) < 1000
  threshold: 0
```

## 🔒 Security Best Practices

1. **Service Account Permissions**
   - Use dedicated service accounts for DataMetronome
   - Grant minimum required permissions
   - Use `roles/bigquery.dataViewer` for read-only checks
   - Never use owner or admin roles

2. **Credential Storage**
   - Store credentials outside the repository
   - Use environment variables in production
   - Rotate credentials regularly
   - Use secret management services (GCP Secret Manager, HashiCorp Vault)

3. **Network Security**
   - Enable VPC Service Controls if available
   - Use private IP addresses for BigQuery access
   - Implement firewall rules

4. **Audit & Monitoring**
   - Enable BigQuery audit logs
   - Monitor query costs and usage
   - Set up alerts for unusual activity

## 💰 Cost Optimization

BigQuery charges for:
- Query processing (per TB scanned)
- Storage (per GB per month)
- Streaming inserts

### Tips to Reduce Costs:

1. **Use Partitioned Tables**
   ```sql
   SELECT * FROM events
   WHERE DATE(created_at) = CURRENT_DATE()
   -- Uses partition pruning, scans less data
   ```

2. **Limit Query Scope**
   ```sql
   SELECT user_id, email FROM users  -- Better
   SELECT * FROM users               -- Scans more data
   ```

3. **Schedule Checks Wisely**
   - Run expensive checks during off-peak hours
   - Adjust check frequency based on data update patterns
   - Use hourly checks only for critical data

4. **Use Table Sampling**
   ```sql
   SELECT * FROM users TABLESAMPLE SYSTEM (10 PERCENT)
   ```

5. **Monitor Query Costs**
   ```python
   # BigQuery job will show bytes processed
   query_job = client.query(sql)
   bytes_processed = query_job.total_bytes_processed
   cost_estimate = (bytes_processed / 1_000_000_000_000) * 5  # $5 per TB
   ```

## 📈 Performance Tips

1. **Connection Pooling**
   - Reuse BigQuery client instances
   - Close connections when done

2. **Async Operations**
   - All operations are async by default
   - Use `asyncio.gather()` for parallel queries

3. **Batch Operations**
   - Batch multiple writes together
   - Use streaming inserts for real-time data

4. **Query Optimization**
   - Use WHERE clauses to filter early
   - Avoid SELECT * when possible
   - Use appropriate JOIN strategies

## 🧪 Testing

### Unit Tests

```python
import pytest
from metronome_pulse_bigquery import BigQueryPulse

@pytest.mark.asyncio
async def test_bigquery_connection():
    pulse = BigQueryPulse(
        project_id="test-project",
        credentials_json=test_credentials,
        dataset="test_dataset"
    )

    await pulse.connect()
    assert await pulse.is_connected()
    await pulse.close()
```

### Integration Tests

```bash
# Set test credentials
export BIGQUERY_TEST_PROJECT=test-project
export BIGQUERY_TEST_CREDENTIALS=/path/to/test-credentials.json

# Run tests
pytest tests/test_bigquery_integration.py -v
```

## 🐛 Troubleshooting

### Common Issues

1. **"Permission Denied" Errors**
   - Check service account has required roles
   - Verify credentials file is readable
   - Ensure BigQuery API is enabled

2. **"Dataset Not Found"**
   - Verify dataset exists in the project
   - Check dataset location matches configuration
   - Ensure service account has access to dataset

3. **"Quota Exceeded"**
   - Check BigQuery quotas in GCP Console
   - Request quota increase if needed
   - Implement rate limiting in checks

4. **Slow Queries**
   - Add indexes/partitions to tables
   - Optimize SQL queries
   - Use EXPLAIN to analyze query plan

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

pulse = BigQueryPulse(...)
await pulse.connect()
```

## 📚 Additional Resources

- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices)
- [BigQuery Pricing](https://cloud.google.com/bigquery/pricing)
- [DataMetronome Documentation](https://github.com/datametronome/datametronome)
- [Example Configurations](./examples/demo-bigquery.yaml)

## 🆘 Support

For issues or questions:
- GitHub Issues: [datametronome/datametronome](https://github.com/datametronome/datametronome/issues)
- Email: team@datametronome.dev
- Documentation: [docs/](../../docs/)
