# API Import Guide - No Scripts Needed! 🚀

You can now import staves and clefs directly via the REST API without needing any scripts!

## 📋 Available Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/config/import` | POST | Import from JSON body |
| `/api/v1/config/import/yaml` | POST | Upload YAML file |
| `/api/v1/config/import/json` | POST | Upload JSON file |
| `/api/v1/staves` | POST | Create single stave |
| `/api/v1/clefs` | POST | Create single clef |

## 🎯 Quick Start: Import BigQuery Stave

### Method 1: JSON Body (Easiest!)

```bash
# Set your environment variables first
export BIGQUERY_PROJECT_ID=your-gcp-project
export BIGQUERY_CREDENTIALS_PATH=/path/to/credentials.json

# Import via API
curl -X POST "http://localhost:8000/api/v1/config/import" \
  -H "Content-Type: application/json" \
  -d '{
    "staves": [
      {
        "id": "stave-bigquery-001",
        "name": "BigQuery Analytics",
        "description": "Production BigQuery database",
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
        "id": "clef-bigquery-email-null",
        "stave_id": "stave-bigquery-001",
        "name": "Email NULL Check",
        "description": "Ensures emails are never null",
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

**Response:**
```json
{
  "success": true,
  "staves_created": 1,
  "clefs_created": 1,
  "staves_deleted": 0,
  "clefs_deleted": 0,
  "errors": [],
  "warnings": []
}
```

### Method 2: Upload YAML File

```bash
curl -X POST "http://localhost:8000/api/v1/config/import/yaml" \
  -F "file=@examples/demo-complete.yaml" \
  -F "clean=false"
```

### Method 3: Upload JSON File

```bash
# First convert YAML to JSON (if needed)
python -c "import yaml, json, sys; print(json.dumps(yaml.safe_load(open('examples/demo-complete.yaml'))))" > config.json

# Then upload
curl -X POST "http://localhost:8000/api/v1/config/import/json" \
  -F "file=@config.json"
```

## 🔄 Update Existing Configuration (Clean Import)

To replace existing staves/clefs with matching IDs:

```bash
# JSON body with clean flag
curl -X POST "http://localhost:8000/api/v1/config/import" \
  -H "Content-Type: application/json" \
  -d '{
    "staves": [...],
    "clefs": [...],
    "clean": true
  }'

# Or with file upload
curl -X POST "http://localhost:8000/api/v1/config/import/yaml?clean=true" \
  -F "file=@examples/demo-complete.yaml"
```

## 🎨 Create Single Items

### Create a Single Stave

```bash
curl -X POST "http://localhost:8000/api/v1/staves" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My BigQuery",
    "description": "My BigQuery database",
    "data_source_type": "bigquery",
    "connection_config": {
      "project_id": "my-project",
      "credentials_path": "/path/to/creds.json",
      "dataset": "analytics"
    },
    "is_active": true
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My BigQuery",
  "data_source_type": "bigquery",
  "connection_config": {...},
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Create a Single Clef

```bash
curl -X POST "http://localhost:8000/api/v1/clefs" \
  -H "Content-Type: application/json" \
  -d '{
    "stave_id": "stave-bigquery-001",
    "name": "Row Count Check",
    "description": "Monitor table row count",
    "check_type": "row_count",
    "config": {
      "table": "users",
      "min_rows": 100
    },
    "schedule": "0 */4 * * *",
    "is_active": true
  }'
```

## 📊 Complete Example: Import All BigQuery Configuration

Here's a complete example to import BigQuery stave with multiple checks:

```bash
curl -X POST "http://localhost:8000/api/v1/config/import" \
  -H "Content-Type: application/json" \
  -d '{
    "staves": [
      {
        "id": "stave-bigquery-prod",
        "name": "Production BigQuery",
        "data_source_type": "bigquery",
        "connection_config": {
          "project_id": "my-company-prod",
          "credentials_path": "/secure/bigquery-creds.json",
          "dataset": "analytics",
          "location": "US"
        },
        "is_active": true
      }
    ],
    "clefs": [
      {
        "id": "clef-users-email-null",
        "stave_id": "stave-bigquery-prod",
        "name": "Users Email NULL Check",
        "check_type": "null_check",
        "config": {
          "table": "users",
          "column": "email",
          "threshold": 0.0
        },
        "schedule": "0 */6 * * *",
        "is_active": true
      },
      {
        "id": "clef-events-freshness",
        "stave_id": "stave-bigquery-prod",
        "name": "Events Freshness Check",
        "check_type": "freshness",
        "config": {
          "table": "events",
          "timestamp_column": "created_at",
          "max_age_hours": 24
        },
        "schedule": "0 */1 * * *",
        "is_active": true
      },
      {
        "id": "clef-orders-range",
        "stave_id": "stave-bigquery-prod",
        "name": "Order Amount Range Check",
        "check_type": "range_check",
        "config": {
          "table": "orders",
          "column": "amount",
          "min_value": 0,
          "max_value": 100000,
          "threshold": 0.01
        },
        "schedule": "0 */4 * * *",
        "is_active": true
      },
      {
        "id": "clef-users-email-pattern",
        "stave_id": "stave-bigquery-prod",
        "name": "Email Pattern Check",
        "check_type": "pattern_check",
        "config": {
          "table": "users",
          "column": "email",
          "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}$",
          "threshold": 0.02
        },
        "schedule": "0 8 * * *",
        "is_active": true
      }
    ]
  }'
```

## 🐍 Python Example

No need for scripts, but if you prefer Python:

```python
import requests

# Configuration
config = {
    "staves": [{
        "id": "stave-bigquery-001",
        "name": "BigQuery Analytics",
        "data_source_type": "bigquery",
        "connection_config": {
            "project_id": "my-project",
            "credentials_path": "/path/to/creds.json",
            "dataset": "analytics"
        },
        "is_active": True
    }],
    "clefs": [{
        "id": "clef-null-check",
        "stave_id": "stave-bigquery-001",
        "name": "Email NULL Check",
        "check_type": "null_check",
        "config": {
            "table": "users",
            "column": "email",
            "threshold": 0.0
        },
        "schedule": "0 */6 * * *",
        "is_active": True
    }]
}

# Import
response = requests.post(
    "http://localhost:8000/api/v1/config/import",
    json=config
)

print(response.json())
# Output: {"success": true, "staves_created": 1, "clefs_created": 1, ...}
```

## 🔍 View Imported Configuration

### List All Staves

```bash
curl "http://localhost:8000/api/v1/staves"
```

### Get Specific Stave

```bash
curl "http://localhost:8000/api/v1/staves/stave-bigquery-001"
```

### List All Clefs

```bash
curl "http://localhost:8000/api/v1/clefs"
```

### List Clefs for a Stave

```bash
curl "http://localhost:8000/api/v1/clefs?stave_id=stave-bigquery-001"
```

## 📝 Interactive API Documentation

Once the API is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can test all endpoints directly from the browser!

## ✅ Benefits of API Import

1. **No Scripts Needed** - Just curl or HTTP requests
2. **Works Everywhere** - Any language, any tool
3. **CI/CD Friendly** - Easy to automate
4. **Interactive Testing** - Use Swagger UI
5. **Programmatic** - Integrate with your tools
6. **Clean Import** - Replace existing configs easily

## 🔄 Comparison: Scripts vs API

| Feature | Script | API |
|---------|--------|-----|
| Requires Python | ✅ Yes | ❌ No |
| Works remotely | ❌ No | ✅ Yes |
| CI/CD friendly | ⚠️ Limited | ✅ Perfect |
| Browser testable | ❌ No | ✅ Yes (Swagger) |
| Any language | ❌ Python only | ✅ Any HTTP client |
| Authentication | N/A | ✅ Token-based |

## 🎉 Summary

**Before (Scripts):**
```bash
cd datametronome/podium
python scripts/import_yaml.py examples/demo-complete.yaml
```

**Now (API - Much Better!):**
```bash
# From anywhere, even remotely!
curl -X POST "http://localhost:8000/api/v1/config/import/yaml" \
  -F "file=@config.yaml"
```

Or even simpler:
```bash
# Just send JSON directly!
curl -X POST "http://localhost:8000/api/v1/config/import" \
  -H "Content-Type: application/json" \
  -d @bigquery-config.json
```

**No more ad-hoc scripts needed! 🎉**

