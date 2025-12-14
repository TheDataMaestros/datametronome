# 📝 YAML Configuration Guide for Staves

Yes! Staves can be configured using **YAML files** for easy, declarative setup.

## 🎯 Three Ways to Configure Staves

### 1. **YAML Files** (Easiest, most readable) ⭐
```yaml
# staves.yaml
staves:
  - name: Production DB
    data_source_type: postgres
    connection_config:
      host: ${DB_HOST}
      port: 5432
```

### 2. **Python Code** (Programmatic)
```python
from datametronome_podium.services.stave_service import create_postgres_stave

stave = create_postgres_stave(name="Production DB", host="localhost", ...)
```

### 3. **REST API** (Remote/Dynamic)
```bash
curl -X POST http://localhost:8000/api/v1/staves -d '{...}'
```

---

## 📋 YAML Configuration Format

### Multi-Stave Format

Use this for configuring multiple data sources at once:

```yaml
# staves.yaml
staves:
  - id: stave-prod-001
    name: Production PostgreSQL
    description: Main production database
    data_source_type: postgres
    connection_config:
      host: db.example.com
      port: 5432
      database: prod_db
      user: monitor_user
      password: ${POSTGRES_PASSWORD}
    is_active: true

  - id: stave-cache-001
    name: Redis Cache
    data_source_type: redis
    connection_config:
      host: redis.example.com
      port: 6379

clefs:
  - id: clef-email-001
    stave_id: stave-prod-001
    name: Email NULL Check
    check_type: null_check
    config:
      table: users
      column: email
      threshold: 0.0
    schedule: "@hourly"
```

### Single-Stave Format

Use this for one data source with its checks:

```yaml
# production-db.yaml
stave:
  name: Production Database
  data_source_type: postgres
  connection_config:
    host: ${DB_HOST}
    port: ${DB_PORT:-5432}
    database: ${DB_NAME}
    user: ${DB_USER}
    password: ${DB_PASSWORD}
  is_active: true

clefs:
  - name: Email Check
    check_type: null_check
    config:
      table: users
      column: email
    schedule: "@hourly"

  - name: Age Range Check
    check_type: range_check
    config:
      table: users
      column: age
      min: 0
      max: 150
    schedule: "@daily"
```

---

## 🔐 Environment Variables

YAML configs support environment variable substitution:

### Basic Usage

```yaml
connection_config:
  host: ${DB_HOST}           # Required variable
  port: ${DB_PORT:-5432}     # Optional with default
  password: ${DB_PASSWORD}   # Required
```

### Set Environment Variables

```bash
# Linux/Mac
export DB_HOST=db.example.com
export DB_PORT=5432
export DB_PASSWORD=secret123

# Windows
set DB_HOST=db.example.com
set DB_PORT=5432
set DB_PASSWORD=secret123

# Or use .env file
echo "DB_HOST=db.example.com" >> .env
echo "DB_PASSWORD=secret123" >> .env
```

---

## 🚀 Using YAML Configurations

### Method 1: Command Line (Easiest)

```bash
# Import staves from YAML
cd datametronome/podium
python scripts/import_staves.py examples/staves.yaml

# Validate without importing
python scripts/import_staves.py examples/staves.yaml --validate-only

# Overwrite existing staves
python scripts/import_staves.py examples/staves.yaml --overwrite
```

### Method 2: Python Code

```python
from datametronome_podium.services.stave_yaml_loader import (
    load_staves_from_yaml,
    import_staves_from_yaml
)
from datametronome_podium.core.database import get_db

# Load from YAML
staves, clefs = load_staves_from_yaml("staves.yaml")

print(f"Loaded {len(staves)} staves:")
for stave in staves:
    print(f"  - {stave.name}")

print(f"\nLoaded {len(clefs)} clefs:")
for clef in clefs:
    print(f"  - {clef.name}")

# Import to database
db = await get_db()
counts = await import_staves_from_yaml("staves.yaml", db)
print(f"Imported {counts['staves']} staves, {counts['clefs']} clefs")
```

### Method 3: Single Stave File

```python
from datametronome_podium.services.stave_yaml_loader import load_single_stave_yaml

# Load a single stave with its checks
stave, clefs = load_single_stave_yaml("production-db.yaml")

print(f"Stave: {stave.name}")
print(f"Checks: {len(clefs)}")
```

---

## 📖 Complete Examples

### Example 1: PostgreSQL Database

```yaml
# postgres.yaml
stave:
  name: Production PostgreSQL
  description: Main production database
  data_source_type: postgres
  connection_config:
    host: ${POSTGRES_HOST}
    port: ${POSTGRES_PORT:-5432}
    database: ${POSTGRES_DB}
    user: ${POSTGRES_USER}
    password: ${POSTGRES_PASSWORD}
    ssl_mode: require
    connect_timeout: 30

clefs:
  - name: User Email Required
    check_type: null_check
    config:
      table: users
      column: email
      threshold: 0.0
    schedule: "@hourly"

  - name: User Age Range
    check_type: range_check
    config:
      table: users
      column: age
      min: 0
      max: 150
    schedule: "@daily"

  - name: Minimum User Count
    check_type: volume_check
    config:
      table: users
      expected_min: 1000
    schedule: "0 8 * * *"
```

### Example 2: Multiple Data Sources

```yaml
# all-sources.yaml
staves:
  # PostgreSQL
  - name: Production DB
    data_source_type: postgres
    connection_config:
      host: ${PG_HOST}
      database: ${PG_DB}
      user: ${PG_USER}
      password: ${PG_PASSWORD}

  # Redis Cache
  - name: Session Cache
    data_source_type: redis
    connection_config:
      host: ${REDIS_HOST}
      port: ${REDIS_PORT:-6379}
      password: ${REDIS_PASSWORD}

  # MongoDB
  - name: Document Store
    data_source_type: mongodb
    connection_config:
      uri: ${MONGO_URI}
      database: documents

clefs:
  - name: User Table Check
    stave_id: stave-prod-db
    check_type: null_check
    config:
      table: users
      column: email
    schedule: "@hourly"
```

### Example 3: Development Environment

```yaml
# dev.yaml
staves:
  - name: Local Dev DB
    data_source_type: sqlite
    connection_config:
      path: ./data/dev.db
    is_active: true

clefs:
  - name: Test Data Check
    check_type: volume_check
    config:
      table: test_users
      expected_min: 10
    schedule: "@daily"
```

---

## ✅ Validation

Validate your YAML configuration before importing:

```bash
# Validate configuration
python scripts/import_staves.py staves.yaml --validate-only
```

This checks:
- ✅ YAML syntax is valid
- ✅ All required fields are present
- ✅ Data source types are supported
- ✅ Check types are supported
- ✅ Stave IDs are unique
- ✅ Clef stave_ids reference valid staves
- ⚠️ Environment variables are set

---

## 🎯 Best Practices

### 1. Use Environment Variables for Secrets

**Good:**
```yaml
connection_config:
  password: ${DB_PASSWORD}
```

**Bad:**
```yaml
connection_config:
  password: "hardcoded_password_123"  # Never do this!
```

### 2. One File Per Environment

```
configs/
  ├── production.yaml
  ├── staging.yaml
  └── development.yaml
```

### 3. Provide Defaults

```yaml
port: ${DB_PORT:-5432}  # Defaults to 5432 if not set
```

### 4. Use Descriptive Names

```yaml
name: "Production User Database - Read Replica"  # Good
name: "db1"                                       # Bad
```

### 5. Add Descriptions

```yaml
description: |
  Main production PostgreSQL database containing user accounts,
  profiles, and authentication data. Read-only monitoring user.
```

---

## 🔄 Workflow Example

### Setup New Database Monitoring

1. **Create YAML config:**

```yaml
# new-db.yaml
stave:
  name: New Application Database
  data_source_type: postgres
  connection_config:
    host: ${DB_HOST}
    database: app_db
    user: monitor
    password: ${DB_PASSWORD}

clefs:
  - name: Email Check
    check_type: null_check
    config:
      table: users
      column: email
    schedule: "@hourly"
```

2. **Set environment variables:**

```bash
export DB_HOST=new-db.example.com
export DB_PASSWORD=secure_password
```

3. **Validate:**

```bash
python scripts/import_staves.py new-db.yaml --validate-only
```

4. **Import:**

```bash
python scripts/import_staves.py new-db.yaml
```

5. **Verify:**

Check the database or API:
```bash
curl http://localhost:8000/api/v1/staves
```

---

## 🛠️ Troubleshooting

### Issue: "Environment variable not set"

**Problem:**
```
❌ Environment variable ${DB_PASSWORD} is required but not set
```

**Solution:**
```bash
export DB_PASSWORD=your_password
```

### Issue: "Duplicate stave IDs"

**Problem:**
```yaml
staves:
  - id: stave-001
    name: DB 1
  - id: stave-001  # Duplicate!
    name: DB 2
```

**Solution:** Remove `id` field to auto-generate unique IDs:
```yaml
staves:
  - name: DB 1  # ID will be auto-generated
  - name: DB 2  # ID will be auto-generated
```

### Issue: "Clef references non-existent stave_id"

**Problem:**
```yaml
clefs:
  - stave_id: wrong-id  # Doesn't exist
```

**Solution:**
- Use correct stave_id from staves section
- Or omit stave_id in single-stave format (auto-assigned)

---

## 📚 Additional Resources

- **Example files:** `examples/staves.yaml`, `examples/production-db.yaml`
- **Python API:** `services/stave_yaml_loader.py`
- **Import script:** `scripts/import_staves.py`
- **Model docs:** `models/stave.py`, `models/clef.py`

---

## 🎓 Quick Reference

### Field Reference

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `id` | No | string | Unique identifier (auto-generated if omitted) |
| `name` | Yes | string | Human-readable name |
| `description` | No | string | Detailed description |
| `data_source_type` | Yes | string | Type of data source |
| `connection_config` | Yes | dict | Connection parameters |
| `is_active` | No | boolean | Active status (default: true) |

### Supported Data Sources

- `postgres`, `postgresql` - PostgreSQL
- `mysql` - MySQL
- `sqlite` - SQLite
- `mongodb` - MongoDB
- `redis` - Redis
- `snowflake` - Snowflake
- `bigquery` - BigQuery
- `api`, `http` - HTTP APIs

### Supported Check Types

- `null_check` - NULL value check
- `uniqueness_check` - Duplicate check
- `range_check` - Value range check
- `pattern_check` - Pattern/regex check
- `volume_check` - Row count check
- `freshness_check` - Data freshness check
- `custom_sql` - Custom SQL query

---

**Ready to start?** Check out the examples:

```bash
cd datametronome/podium
cat examples/staves.yaml
cat examples/production-db.yaml
```

Then import them:

```bash
python scripts/import_staves.py examples/staves.yaml --validate-only
```

Happy monitoring! 🎵
