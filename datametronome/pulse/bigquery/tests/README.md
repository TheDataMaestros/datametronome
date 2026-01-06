# BigQuery Connector Tests

These are **read-only** integration tests that require **real BigQuery credentials** and will actually connect to Google Cloud Platform.

⚠️ **Important**: These tests only perform READ operations on existing tables. They do NOT create, modify, or delete any data. This matches the actual use case of data quality monitoring tools.

## Setup Instructions

### 1. Required Environment Variables

Set the following environment variables before running tests:

```bash
# Required: Your GCP project ID
export BIGQUERY_TEST_PROJECT_ID="your-gcp-project-id"

# Option 1: Path to service account JSON file
export BIGQUERY_TEST_CREDENTIALS_PATH="/path/to/service-account-key.json"

# Option 2: Service account JSON as string (alternative to path)
export BIGQUERY_TEST_CREDENTIALS_JSON='{"type":"service_account",...}'

# Optional: Test dataset name (default: datametronome_test)
export BIGQUERY_TEST_DATASET="datametronome_test"

# Optional: BigQuery location (default: US)
export BIGQUERY_TEST_LOCATION="US"
```

### 2. Create GCP Service Account

If you don't have credentials yet:

1. **Create a service account:**
   ```bash
   gcloud iam service-accounts create datametronome-test \
       --display-name="DataMetronome Test Account"
   ```

2. **Grant necessary permissions:**
   ```bash
   # Required for creating/deleting datasets and tables
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
       --member="serviceAccount:datametronome-test@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/bigquery.admin"
   ```

3. **Create and download key:**
   ```bash
   gcloud iam service-accounts keys create ~/bigquery-test-key.json \
       --iam-account=datametronome-test@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

4. **Set environment variable:**
   ```bash
   export BIGQUERY_TEST_CREDENTIALS_PATH="$HOME/bigquery-test-key.json"
   export BIGQUERY_TEST_PROJECT_ID="YOUR_PROJECT_ID"
   ```

### 3. Alternative: Use Application Default Credentials

If you're already authenticated with `gcloud auth application-default login`, you can skip the credentials path:

```bash
export BIGQUERY_TEST_PROJECT_ID="your-gcp-project-id"
# Omit BIGQUERY_TEST_CREDENTIALS_PATH - will use default credentials
```

## Running Tests

### Run all integration tests:
```bash
cd datametronome/pulse/bigquery
pytest tests/ -v -m integration
```

### Run specific test file:
```bash
pytest tests/test_integration.py -v
```

### Run specific test:
```bash
pytest tests/test_integration.py::TestBigQueryPulseIntegration::test_connection_lifecycle -v
```

### Run tests with verbose output:
```bash
pytest tests/ -v -s
```

## Test Behavior

- **Read-only operations only**: Tests only perform READ operations (queries, schema inspection, table listing)
- **Uses existing datasets and tables**: Tests use existing datasets and tables in your project
- **No data modification**: Tests do NOT create, modify, or delete any data
- **Skipping**: Tests are automatically skipped if:
  - Required environment variables are not set
  - No existing datasets are found in the project
  - No existing tables are found in the dataset (for table-specific tests)
- **Real operations**: Tests perform actual BigQuery read operations similar to data quality checks

## Test Coverage

The integration tests cover read-only operations needed for data quality monitoring:
- Connection lifecycle (connect, disconnect, health checks)
- Async context manager support
- Read operations (queries, parameterized queries with different types)
- Table metadata (schema info, list tables)
- Data quality style queries (row counts, filtered queries)
- Readonly connector functionality

## Prerequisites

**You need at least one existing dataset in your BigQuery project.**

If you don't have any datasets, create one:

```bash
# Using gcloud CLI
bq mk --dataset --location=US gen-lang-client-0489056598:datametronome_test

# Or using the BigQuery console
# Go to https://console.cloud.google.com/bigquery
# Click "Create Dataset" and create a dataset
```

## Cost Considerations

⚠️ **Note**: These tests only perform read queries on existing tables:
- Query costs: Minimal (simple COUNT and SELECT queries)
- No storage costs: Tests don't create any tables or data
- No write costs: Tests are completely read-only

To minimize costs:
- Use a test GCP project with budget alerts
- Tests use LIMIT clauses to keep query costs low
- Tests query existing tables (no data creation)

## Troubleshooting

### "Permission Denied" errors
- Verify service account has `roles/bigquery.admin` or equivalent permissions
- Check that credentials file is readable
- Ensure BigQuery API is enabled: `gcloud services enable bigquery.googleapis.com`

### "Dataset not found" errors
- Tests automatically create datasets - this should not happen
- Check that project ID is correct
- Verify credentials have permission to create datasets

### Tests are skipped
- Check environment variables are set correctly
- Run `echo $BIGQUERY_TEST_PROJECT_ID` to verify
- Tests will show "SKIPPED" in output if credentials are missing
