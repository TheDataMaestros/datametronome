# 📋 Stave Configuration Examples

This document shows you exactly what Stave configurations look like for different data sources.

## 🏗️ Stave Structure

A Stave has this structure:

```python
{
    "id": "stave-abc123",              # Unique identifier
    "name": "Production Database",     # Human-readable name
    "description": "...",              # Optional description
    "data_source_type": "postgres",    # Type of data source
    "connection_config": { ... },      # Connection parameters (varies by type)
    "is_active": true,                 # Whether monitoring is active
    "created_at": "2025-01-01T12:00:00",
    "updated_at": "2025-01-01T12:00:00"
}
```

The **`connection_config`** varies by data source type. Here are examples:

---

## 📊 PostgreSQL Stave

```python
{
    "id": "stave-prod-pg-001",
    "name": "Production PostgreSQL",
    "description": "Main production database for user data",
    "data_source_type": "postgres",
    "connection_config": {
        "host": "db.example.com",
        "port": 5432,
        "database": "prod_db",
        "user": "monitor_user",
        "password": "secure_password",
        # Optional parameters:
        "ssl_mode": "require",
        "connect_timeout": 30,
        "application_name": "datametronome"
    },
    "is_active": true,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}
```

**Required fields:**
- `host` - Database hostname
- `database` - Database name
- `user` - Username

**Optional fields:**
- `port` - Port (default: 5432)
- `password` - Password
- `ssl_mode` - SSL connection mode
- `connect_timeout` - Connection timeout in seconds

---

## 📦 SQLite Stave

```python
{
    "id": "stave-local-sqlite-001",
    "name": "Local Analytics DB",
    "description": "Local SQLite database for analytics",
    "data_source_type": "sqlite",
    "connection_config": {
        "path": "/data/analytics.db",
        # Optional parameters:
        "timeout": 5.0,
        "check_same_thread": false
    },
    "is_active": true,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}
```

**Required fields:**
- `path` - Path to SQLite database file

**Optional fields:**
- `timeout` - Connection timeout
- `check_same_thread` - Thread safety setting

---

## 🐬 MySQL Stave

```python
{
    "id": "stave-app-mysql-001",
    "name": "Application MySQL",
    "description": "MySQL database for application backend",
    "data_source_type": "mysql",
    "connection_config": {
        "host": "mysql.example.com",
        "port": 3306,
        "database": "app_db",
        "user": "readonly_user",
        "password": "mysql_password",
        # Optional parameters:
        "charset": "utf8mb4",
        "connect_timeout": 30
    },
    "is_active": true,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}
```

**Required fields:**
- `host` - Database hostname
- `database` - Database name
- `user` - Username

**Optional fields:**
- `port` - Port (default: 3306)
- `password` - Password
- `charset` - Character set
- `connect_timeout` - Connection timeout

---

## 🔴 Redis Stave

```python
{
    "id": "stave-cache-redis-001",
    "name": "Production Cache",
    "description": "Redis cache for session data",
    "data_source_type": "redis",
    "connection_config": {
        "host": "redis.example.com",
        "port": 6379,
        "db": 0,
        # Optional parameters:
        "password": "redis_password",
        "ssl": true,
        "socket_timeout": 5,
        "socket_connect_timeout": 5
    },
    "is_active": true,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}
```

**Required fields:**
- `host` - Redis hostname

**Optional fields:**
- `port` - Port (default: 6379)
- `db` - Database number (default: 0)
- `password` - Password
- `ssl` - Use SSL connection

---

## 🍃 MongoDB Stave

```python
{
    "id": "stave-docs-mongo-001",
    "name": "Document Store",
    "description": "MongoDB for document storage",
    "data_source_type": "mongodb",
    "connection_config": {
        "uri": "mongodb://user:pass@mongo.example.com:27017/",
        "database": "documents",
        # Or individual parameters:
        # "host": "mongo.example.com",
        # "port": 27017,
        # "username": "user",
        # "password": "pass",
        # "database": "documents",
        # Optional:
        "authSource": "admin",
        "retryWrites": true,
        "w": "majority"
    },
    "is_active": true,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}
```

**Required fields:**
- `uri` - MongoDB connection URI, OR
- `host` + `database` - Individual parameters

**Optional fields:**
- `authSource` - Authentication database
- `retryWrites` - Enable retry writes
- MongoDB connection options

---

## ❄️ Snowflake Stave

```python
{
    "id": "stave-warehouse-sf-001",
    "name": "Snowflake Data Warehouse",
    "description": "Cloud data warehouse",
    "data_source_type": "snowflake",
    "connection_config": {
        "account": "abc12345.us-east-1",
        "user": "monitor_user",
        "password": "snowflake_password",
        "warehouse": "COMPUTE_WH",
        "database": "ANALYTICS",
        "schema": "PUBLIC",
        # Optional parameters:
        "role": "MONITOR_ROLE",
        "timeout": 120
    },
    "is_active": true,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}
```

**Required fields:**
- `account` - Snowflake account identifier
- `user` - Username
- `warehouse` - Warehouse name
- `database` - Database name

**Optional fields:**
- `password` or authentication method
- `schema` - Schema name
- `role` - Role to use

---

## 🌐 BigQuery Stave

```python
{
    "id": "stave-bigquery-001",
    "name": "Google BigQuery",
    "description": "BigQuery analytics database",
    "data_source_type": "bigquery",
    "connection_config": {
        "project_id": "my-gcp-project",
        "dataset": "analytics",
        "credentials_path": "/path/to/service-account.json",
        # Or credentials JSON directly:
        # "credentials_json": {...},
        # Optional:
        "location": "US",
        "timeout": 60
    },
    "is_active": true,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}
```

**Required fields:**
- `project_id` - GCP project ID
- `credentials_path` or `credentials_json` - Authentication

**Optional fields:**
- `dataset` - Default dataset
- `location` - Data location
- `timeout` - Query timeout

---

## 🌍 HTTP API Stave

```python
{
    "id": "stave-api-external-001",
    "name": "External API",
    "description": "REST API for external service",
    "data_source_type": "api",
    "connection_config": {
        "base_url": "https://api.example.com",
        "api_key": "your_api_key",
        # Optional parameters:
        "headers": {
            "Authorization": "Bearer token",
            "User-Agent": "DataMetronome/1.0"
        },
        "timeout": 30,
        "verify_ssl": true
    },
    "is_active": true,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
}
```

**Required fields:**
- `base_url` - Base URL of the API

**Optional fields:**
- `api_key` - API key for authentication
- `headers` - Custom HTTP headers
- `timeout` - Request timeout
- `verify_ssl` - Verify SSL certificates

---

## 💾 In Database Storage

When stored in the SQLite database, the `connection_config` is saved as a JSON string:

```sql
-- Database row
id                  = 'stave-prod-pg-001'
name                = 'Production PostgreSQL'
description         = 'Main production database'
data_source_type    = 'postgres'
connection_config   = '{"host":"db.example.com","port":5432,"database":"prod_db","user":"monitor_user","password":"secure_password"}'
is_active           = 1
created_at          = '2025-01-15T10:30:00'
updated_at          = '2025-01-15T10:30:00'
```

Use the helper functions to handle serialization:

```python
from datametronome_podium.services.stave_service import serialize_stave, deserialize_stave

# Before saving
db_data = serialize_stave(stave)  # Converts dict to JSON string

# After loading
stave = deserialize_stave(db_row)  # Converts JSON string to dict
```

---

## 🔧 Creating Staves in Code

### Easy Way (Using Helpers)

```python
from datametronome_podium.services.stave_service import create_postgres_stave

stave = create_postgres_stave(
    name="Production DB",
    host="db.example.com",
    database="prod_db",
    user="monitor_user",
    password="secure_password",
    port=5432
)
```

### Manual Way (Direct Model)

```python
from datametronome_podium.models.stave import Stave

stave = Stave(
    id="stave-prod-001",  # Or leave None for auto-generation
    name="Production DB",
    data_source_type="postgres",
    connection_config={
        "host": "db.example.com",
        "port": 5432,
        "database": "prod_db",
        "user": "monitor_user",
        "password": "secure_password"
    },
    is_active=True
)
```

### Via API (JSON)

```bash
curl -X POST http://localhost:8000/api/v1/staves \
  -H "Content-Type: application/json" \
  -d '{
    "id": "stave-prod-001",
    "name": "Production DB",
    "description": "Main database",
    "data_source_type": "postgres",
    "connection_config": {
      "host": "db.example.com",
      "port": 5432,
      "database": "prod_db",
      "user": "monitor_user",
      "password": "secure_password"
    },
    "is_active": true,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
  }'
```

---

## 🔒 Security Notes

**Important:**
- ⚠️ Connection configs contain sensitive credentials
- 🔐 In production, encrypt the `connection_config` field
- 🔑 Consider using environment variables or secrets management
- 🚫 Never commit real credentials to version control

**Future Enhancement:**
```python
# TODO: Add credential encryption
from datametronome_podium.core.security import encrypt_config, decrypt_config

# When saving
encrypted_config = encrypt_config(stave.connection_config)

# When loading
decrypted_config = decrypt_config(encrypted_config)
```

---

## 📝 Configuration Validation

The Stave model validates configurations automatically:

```python
# ✅ Valid - will work
stave = Stave(
    name="Test DB",
    data_source_type="postgres",
    connection_config={"host": "localhost"}
)

# ❌ Invalid - empty config
stave = Stave(
    name="Test DB",
    data_source_type="postgres",
    connection_config={}  # Error: connection_config cannot be empty
)

# ❌ Invalid - unsupported type
stave = Stave(
    name="Test DB",
    data_source_type="oracle",  # Error: Unsupported data source type
    connection_config={"host": "localhost"}
)

# ❌ Invalid - empty name
stave = Stave(
    name="   ",  # Error: name cannot be empty or whitespace
    data_source_type="postgres",
    connection_config={"host": "localhost"}
)
```

---

## 🎯 Quick Reference

| Data Source | Required Config Fields |
|-------------|----------------------|
| PostgreSQL  | `host`, `database`, `user` |
| MySQL       | `host`, `database`, `user` |
| SQLite      | `path` |
| MongoDB     | `uri` OR `host` + `database` |
| Redis       | `host` |
| Snowflake   | `account`, `user`, `warehouse`, `database` |
| BigQuery    | `project_id`, `credentials_path` |
| API         | `base_url` |

---

## 💡 Tips

1. **Use helper functions** - `create_postgres_stave()` is easier than manual construction
2. **IDs are optional** - Leave blank for auto-generation
3. **Types are flexible** - "postgres" and "postgresql" both work
4. **Minimal config works** - Only provide what you need
5. **Add what you want** - Extra config fields are preserved

---

**Need more examples?** Check out:
- `tests/test_stave_examples.py` - Working code examples
- `STAVES_QUICKSTART.md` - Quick start guide
- `models/stave.py` - Model source with docstrings

