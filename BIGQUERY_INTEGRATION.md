# BigQuery Integration for DataMetronome

## 🎉 Overview

BigQuery support has been successfully integrated into DataMetronome using the **DataPulse** architecture! You can now create staves (data sources) for BigQuery and run data quality checks (clefs) against your BigQuery datasets.

## 📦 What's Included

### 1. BigQuery DataPulse Connector (`metronome-pulse-bigquery`)

A complete, async-first BigQuery connector package located at:
```
datametronome/pulse/bigquery/
```

**Features:**
- ⚡ Async-first design using asyncio
- 🔐 Service account authentication
- 📊 Full read/write operations
- 🛡️ Type-safe implementation
- 📈 Optimized for performance
- 🌍 Multi-region support (US, EU, etc.)

**Components:**
- `BigQueryPulse` - Full read/write connector
- `BigQueryReadonlyPulse` - Read-only connector for data quality checks
- Complete package setup (setup.py, pyproject.toml, README.md)
- Testing infrastructure

### 2. Podium Integration

BigQuery support has been integrated into:

**ClefExecutor Service** (`datametronome/podium/datametronome_podium/services/clef_executor.py`)
- Supports all check types: NULL, row count, uniqueness, range, pattern, freshness, column values
- BigQuery-specific SQL syntax (REGEXP_CONTAINS for patterns)
- Proper connection handling with credentials

**Stave Actions** (`datametronome/podium/datametronome_podium/api/v1/endpoints/stave_actions.py`)
- Data generation support
- Data preview support
- Full integration with BigQuery read/write operations

### 3. Example Configurations

**Demo Configuration:** Integrated into `datametronome/podium/examples/demo-complete.yaml`
- BigQuery stave with environment variable configuration
- Common check types (NULL, freshness, range, pattern)
- Disabled by default (enable when BigQuery credentials are configured)
- All examples in one consolidated demo file

**Setup Guide:** `datametronome/pulse/bigquery/BIGQUERY_SETUP.md`
- Complete setup instructions
- GCP service account configuration
- Security best practices
- Cost optimization tips
- Troubleshooting guide

## 🚀 Quick Start

### 1. Install the BigQuery DataPulse Connector

```bash
cd datametronome/pulse/bigquery
pip install -e .
```

Or install dependencies directly:
```bash
pip install google-cloud-bigquery google-auth
```

### 2. Set Up GCP Credentials

```bash
# Enable BigQuery API
gcloud services enable bigquery.googleapis.com

# Create service account
gcloud iam service-accounts create datametronome-sa \
    --display-name="DataMetronome Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:datametronome-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:datametronome-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"

# Download credentials
gcloud iam service-accounts keys create ~/bigquery-credentials.json \
    --iam-account=datametronome-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 3. Create a BigQuery Stave

**Option A: Using REST API (Easiest! No scripts needed)**

```bash
# Import BigQuery stave and clefs with a single API call
curl -X POST "http://localhost:8000/api/v1/config/import" \
  -H "Content-Type: application/json" \
  -d '{
    "staves": [
      {
        "id": "stave-bigquery-001",
        "name": "BigQuery Analytics",
        "data_source_type": "bigquery",
        "connection_config": {
          "project_id": "your-gcp-project",
          "credentials_path": "/path/to/credentials.json",
          "dataset": "analytics",
          "location": "US"
        },
        "is_active": true
      }
    ],
    "clefs": [
      {
        "stave_id": "stave-bigquery-001",
        "name": "Email NULL Check",
        "check_type": "null_check",
        "config": {
          "table": "users",
          "column": "email",
          "threshold": 0.0
        },
        "schedule": "0 */6 * * *",
        "is_active": true
      }
    ]
  }'
```

See [API Import Guide](datametronome/podium/API_IMPORT_GUIDE.md) for more details.

**Option B: Using Python**

```python
import asyncio
from metronome_pulse_bigquery import BigQueryPulse

async def main():
    pulse = BigQueryPulse(
        project_id="your-gcp-project",
        credentials_path="/path/to/credentials.json",
        dataset="analytics"
    )

    await pulse.connect()
    results = await pulse.query("SELECT * FROM users LIMIT 10")
    print(f"Found {len(results)} users")
    await pulse.close()

asyncio.run(main())
```

**Option C: Using YAML File via API**

Upload the YAML file directly:
```bash
curl -X POST "http://localhost:8000/api/v1/config/import/yaml" \
  -F "file=@examples/demo-complete.yaml"
```

**Option D: Using YAML Configuration (Script)**

The BigQuery stave is included in `demo-complete.yaml`. To use it:

1. Set environment variables:
   ```bash
   export BIGQUERY_PROJECT_ID=your-gcp-project
   export BIGQUERY_CREDENTIALS_PATH=/path/to/credentials.json
   ```

2. Enable the BigQuery stave and clefs in `demo-complete.yaml`:
   ```yaml
   # Change is_active from false to true for BigQuery stave and clefs
   - id: stave-demo-bigquery
     is_active: true  # Enable this

   - id: clef-bigquery-users-email-null
     is_active: true  # Enable this
   ```

3. Import the configuration:
   ```bash
   cd datametronome/podium
   python scripts/import_yaml.py --file examples/demo-complete.yaml
   ```

**Option E: Single Stave via API**

Create just the stave:
```bash
curl -X POST "http://localhost:8000/api/v1/staves" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BigQuery Analytics",
    "data_source_type": "bigquery",
    "connection_config": {
      "project_id": "your-gcp-project",
      "credentials_path": "/path/to/credentials.json",
      "dataset": "analytics"
    },
    "is_active": true
  }'
```

💡 **Recommended:** Use Option A (batch import API) for the easiest setup!

## ✅ Supported Check Types

All data quality check types work with BigQuery:

1. **NULL Check** - Validate no NULL values in columns
2. **Row Count Check** - Ensure expected data volume
3. **Uniqueness Check** - Verify no duplicate values
4. **Range Check** - Validate numeric ranges
5. **Pattern Check** - Regex validation (using REGEXP_CONTAINS)
6. **Freshness Check** - Ensure data is recent
7. **Column Values Check** - Validate allowed values
8. **Custom SQL Check** - Execute custom queries

## 🔧 Configuration Options

### Connection Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `project_id` | Yes | GCP project ID |
| `credentials_path` | Yes* | Path to service account JSON |
| `credentials_json` | Yes* | Service account credentials dict |
| `dataset` | No | Default dataset name |
| `location` | No | BigQuery location (US, EU, etc.) |

*Either `credentials_path` or `credentials_json` required.

### Using Environment Variables

```yaml
connection_config:
  project_id: ${BIGQUERY_PROJECT_ID}
  credentials_path: ${BIGQUERY_CREDENTIALS_PATH}
  dataset: ${BIGQUERY_DATASET}
```

## 🔒 Security Best Practices

1. **Minimal Permissions**
   - Use `roles/bigquery.dataViewer` for read-only checks
   - Use `roles/bigquery.dataEditor` only when writes needed
   - Always include `roles/bigquery.jobUser`

2. **Credential Management**
   - Store credentials outside repository
   - Use environment variables
   - Rotate credentials regularly
   - Consider GCP Secret Manager

3. **Network Security**
   - Enable VPC Service Controls
   - Use private IP when possible
   - Implement firewall rules

## 💰 Cost Optimization

BigQuery charges for queries ($5 per TB scanned). To minimize costs:

1. **Use Partitioned Tables**
   ```sql
   WHERE DATE(created_at) = CURRENT_DATE()
   ```

2. **Limit Query Scope**
   ```sql
   SELECT user_id, email FROM users  -- Better than SELECT *
   ```

3. **Schedule Wisely**
   - Run expensive checks during off-peak hours
   - Adjust frequency based on needs

4. **Monitor Costs**
   - Check query bytes processed
   - Set up budget alerts in GCP

## 📊 Example: BigQuery in Demo Configuration

The BigQuery stave is included in `datametronome/podium/examples/demo-complete.yaml`:

```yaml
staves:
  # BigQuery analytics database
  - id: stave-demo-bigquery
    name: DEMO-BigQuery Analytics
    description: Demo BigQuery analytics database for cloud-scale data quality monitoring
    data_source_type: bigquery
    connection_config:
      project_id: ${BIGQUERY_PROJECT_ID}
      dataset: analytics
      credentials_path: ${BIGQUERY_CREDENTIALS_PATH}
      location: US
    is_active: false  # Enable when configured

clefs:
  # BigQuery checks (disabled by default)
  - id: clef-bigquery-users-email-null
    stave_id: stave-demo-bigquery
    name: 🌐 BigQuery Email NULL Check
    check_type: null_check
    config:
      table: users
      column: email
      threshold: 0.0
    schedule: "0 */6 * * *"
    is_active: false

  - id: clef-bigquery-events-freshness
    stave_id: stave-demo-bigquery
    name: 🌐 BigQuery Events Freshness
    check_type: freshness
    config:
      table: events
      timestamp_column: created_at
      max_age_hours: 24
    schedule: "0 */1 * * *"
    is_active: false

  # ... more checks in demo-complete.yaml
```

**To enable:**
1. Set environment variables
2. Change `is_active: false` to `is_active: true`
3. Import with `python scripts/import_yaml.py --file examples/demo-complete.yaml`

## 🧪 Testing Your BigQuery Integration

1. **Test Connection**
   ```python
   from metronome_pulse_bigquery import BigQueryPulse
   import asyncio

   async def test():
       pulse = BigQueryPulse(
           project_id="your-project",
           credentials_path="/path/to/creds.json"
       )
       await pulse.connect()
       print(f"Connected: {await pulse.is_connected()}")
       await pulse.close()

   asyncio.run(test())
   ```

2. **Test Query**
   ```python
   async def test_query():
       pulse = BigQueryPulse(...)
       await pulse.connect()

       # List tables
       tables = await pulse.list_tables("your_dataset")
       print(f"Tables: {tables}")

       # Query data
       results = await pulse.query("SELECT COUNT(*) as count FROM users")
       print(f"Results: {results}")

       await pulse.close()
   ```

3. **Test via API**
   ```bash
   # Test stave connection
   curl -X POST "http://localhost:8000/api/v1/staves/{stave_id}/test" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

## 📚 Documentation

- **Setup Guide**: `datametronome/pulse/bigquery/BIGQUERY_SETUP.md`
- **Demo Config**: BigQuery examples in `datametronome/podium/examples/demo-complete.yaml`
- **Package README**: `datametronome/pulse/bigquery/README.md`
- **BigQuery Docs**: https://cloud.google.com/bigquery/docs

## 🐛 Troubleshooting

### "Permission Denied" Error
- Verify service account has required roles
- Check credentials file is readable
- Ensure BigQuery API is enabled

### "Dataset Not Found" Error
- Verify dataset exists in your project
- Check dataset location matches config
- Ensure service account has dataset access

### Slow Queries
- Use partitioned tables
- Add WHERE clauses to filter early
- Avoid SELECT * when possible
- Check query costs in BigQuery console

## 🎯 Next Steps

1. **Set up your GCP credentials** following the setup guide
2. **Install the BigQuery connector** package
3. **Create a BigQuery stave** using YAML, Python, or REST API
4. **Add data quality checks** (clefs) for your tables
5. **Schedule checks** and monitor results in the dashboard

## 🤝 Contributing

The BigQuery integration follows the DataPulse architecture:
- Core interfaces: `datametronome/pulse/core/`
- BigQuery implementation: `datametronome/pulse/bigquery/`
- Service integration: `datametronome/podium/`

To add features or improvements:
1. Update the BigQuery connector
2. Add corresponding Podium service integration
3. Update documentation and examples
4. Add tests

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/datametronome/datametronome/issues)
- **Email**: team@datametronome.dev
- **Docs**: `datametronome/docs/`

---

**Happy data quality monitoring with BigQuery! 🎵📊**
