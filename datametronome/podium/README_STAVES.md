# 🎵 Staves & Clefs - Complete Guide

Complete, clear, and functional implementation of Staves (data sources) and Clefs (data quality checks) for DataMetronome.

---

## 📚 What You Have Now

### ✅ Production-Ready Models
- **`models/stave.py`** - Stave (data source) model with validation
- **`models/clef.py`** - Clef (quality check) model with validation
- Comprehensive docstrings with inline examples
- Smart validation and helpful error messages

### ✅ Easy-to-Use Service Layer
- **`services/stave_service.py`** - Helper functions for creating and managing staves
- Pre-built creators: `create_postgres_stave()`, `create_sqlite_stave()`, etc.
- Check creators: `create_null_check()`, `create_range_check()`, etc.
- Serialization helpers for database storage

### ✅ YAML Configuration Support
- **`services/stave_yaml_loader.py`** - Load staves from YAML files
- **`examples/staves.yaml`** - Multi-stave configuration example
- **`examples/production-db.yaml`** - Single-stave configuration example
- **`scripts/import_staves.py`** - CLI tool for importing YAML configs
- Environment variable support (`${VAR_NAME}`)

### ✅ Comprehensive Tests
- **`tests/test_stave_examples.py`** - 21 example-driven tests
- **`tests/test_yaml_loader.py`** - 8 YAML loading tests
- All tests serve as documentation

### ✅ Documentation
- **`STAVES_QUICKSTART.md`** - Quick start guide with examples
- **`STAVE_CONFIGURATIONS.md`** - Configuration format reference
- **`YAML_CONFIG_GUIDE.md`** - Complete YAML guide

---

## 🎯 Three Ways to Configure Staves

### 1. YAML Files (Easiest!) ⭐

```yaml
# staves.yaml
staves:
  - name: Production DB
    data_source_type: postgres
    connection_config:
      host: ${DB_HOST}
      port: 5432
      database: prod_db
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

**Import:**
```bash
python scripts/import_staves.py staves.yaml
```

### 2. Python Code

```python
from datametronome_podium.services.stave_service import (
    create_postgres_stave,
    create_null_check
)

# Create stave
stave = create_postgres_stave(
    name="Production DB",
    host="db.example.com",
    database="prod",
    user="monitor"
)

# Create check
check = create_null_check(
    stave_id=stave.id,
    name="Email Check",
    table="users",
    column="email"
)
```

### 3. REST API

```bash
curl -X POST http://localhost:8000/api/v1/staves \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production DB",
    "data_source_type": "postgres",
    "connection_config": {"host": "localhost", ...}
  }'
```

---

## 🚀 Quick Start

### Option A: Use YAML (Recommended)

1. **Create a YAML file:**

```yaml
# my-database.yaml
stave:
  name: My Production Database
  data_source_type: postgres
  connection_config:
    host: ${DB_HOST}
    database: ${DB_NAME}
    user: ${DB_USER}
    password: ${DB_PASSWORD}

clefs:
  - name: Email Check
    check_type: null_check
    config:
      table: users
      column: email
```

2. **Set environment variables:**

```bash
export DB_HOST=db.example.com
export DB_NAME=prod_db
export DB_USER=monitor
export DB_PASSWORD=secret
```

3. **Import:**

```bash
cd datametronome/podium
python scripts/import_staves.py my-database.yaml
```

### Option B: Use Python

```python
from datametronome_podium.services.stave_service import create_postgres_stave

stave = create_postgres_stave(
    name="Production DB",
    host="db.example.com",
    database="prod",
    user="monitor",
    password="secret"
)

# Save to database
from datametronome_podium.services.stave_service import serialize_stave
from datametronome_podium.core.database import get_db

db = await get_db()
stave_data = serialize_stave(stave)
await db.write([{"table": "staves", **stave_data}], "staves")
```

---

## 📖 Documentation Files

| File | Purpose |
|------|---------|
| `STAVES_QUICKSTART.md` | Quick start guide with copy-paste examples |
| `STAVE_CONFIGURATIONS.md` | All configuration formats and examples |
| `YAML_CONFIG_GUIDE.md` | Complete YAML configuration guide |
| `README_STAVES.md` | This file - overview of everything |

---

## 💡 Examples

### Load from YAML

```python
from datametronome_podium.services.stave_yaml_loader import load_staves_from_yaml

staves, clefs = load_staves_from_yaml("staves.yaml")

print(f"Loaded {len(staves)} staves:")
for stave in staves:
    print(f"  - {stave.name}")
```

### Create Programmatically

```python
from datametronome_podium.services.stave_service import (
    create_postgres_stave,
    create_null_check,
    create_range_check
)

# Create stave
stave = create_postgres_stave(
    name="Production DB",
    host="db.example.com",
    database="prod",
    user="monitor"
)

# Create checks
email_check = create_null_check(
    stave_id=stave.id,
    name="Email Required",
    table="users",
    column="email",
    schedule="@hourly"
)

age_check = create_range_check(
    stave_id=stave.id,
    name="Age Range",
    table="users",
    column="age",
    min_value=0,
    max_value=150,
    schedule="@daily"
)
```

### Load from Database

```python
from datametronome_podium.services.stave_service import deserialize_stave
from datametronome_podium.core.database import get_db

db = await get_db()
rows = await db.query("SELECT * FROM staves WHERE id = ?", [stave_id])
stave = deserialize_stave(rows[0])

print(f"Loaded: {stave.name}")
```

---

## 🧪 Tests as Documentation

Run tests to see working examples:

```bash
# Example-driven unit tests
pytest tests/test_stave_examples.py -v -s

# YAML loader tests
pytest tests/test_yaml_loader.py -v -s

# Run all stave tests
pytest tests/test_stave*.py -v
```

Each test is a working example that you can read and learn from!

---

## 🔧 Supported Data Sources

| Type | Connection Config |
|------|-------------------|
| PostgreSQL | `host`, `port`, `database`, `user`, `password` |
| MySQL | `host`, `port`, `database`, `user`, `password` |
| SQLite | `path` |
| MongoDB | `uri` OR `host` + `database` |
| Redis | `host`, `port`, `db`, `password` |
| Snowflake | `account`, `user`, `warehouse`, `database` |
| BigQuery | `project_id`, `credentials_path` |
| HTTP API | `base_url`, `api_key`, `headers` |

See `STAVE_CONFIGURATIONS.md` for detailed examples of each.

---

## ✅ Supported Check Types

| Type | Purpose |
|------|---------|
| `null_check` | Check for NULL values |
| `uniqueness_check` | Check for duplicates |
| `range_check` | Check value ranges |
| `pattern_check` | Check regex patterns |
| `volume_check` | Check row counts |
| `freshness_check` | Check data recency |
| `custom_sql` | Custom SQL queries |
| `schema_check` | Schema validation |
| `referential_check` | Foreign key integrity |

---

## 📁 File Structure

```
datametronome/podium/
├── datametronome_podium/
│   ├── models/
│   │   ├── stave.py           # Stave model
│   │   └── clef.py            # Clef model
│   ├── services/
│   │   ├── stave_service.py   # Helper functions
│   │   └── stave_yaml_loader.py  # YAML loader
│   └── api/v1/endpoints/
│       ├── staves.py          # Stave API endpoints
│       └── clefs.py           # Clef API endpoints
├── examples/
│   ├── staves.yaml            # Multi-stave example
│   └── production-db.yaml     # Single-stave example
├── scripts/
│   └── import_staves.py       # YAML import CLI
├── tests/
│   ├── test_stave_examples.py # Example-driven tests
│   └── test_yaml_loader.py    # YAML loader tests
└── docs/
    ├── STAVES_QUICKSTART.md
    ├── STAVE_CONFIGURATIONS.md
    ├── YAML_CONFIG_GUIDE.md
    └── README_STAVES.md (this file)
```

---

## 🎯 Design Principles

1. **Clear & Easy** - Simple helper functions, not complex APIs
2. **Well-Documented** - Examples everywhere, inline docs
3. **Functional** - Everything works, all tests pass
4. **Flexible** - YAML, Python, or API - your choice
5. **Developer-Friendly** - Tests serve as documentation

---

## 🚦 Next Steps

1. **Read the quick start:** `STAVES_QUICKSTART.md`
2. **Try an example:** Run `python scripts/import_staves.py examples/staves.yaml --validate-only`
3. **Read the tests:** Open `tests/test_stave_examples.py` and see working code
4. **Create your config:** Make a YAML file for your database
5. **Import it:** Use the import script to load your config

---

## 💬 Questions?

- **"How do I configure a PostgreSQL database?"**  
  See `STAVE_CONFIGURATIONS.md` → PostgreSQL section

- **"Can I use YAML?"**  
  Yes! See `YAML_CONFIG_GUIDE.md` for complete guide

- **"Where are code examples?"**  
  In the test files: `test_stave_examples.py` and `test_yaml_loader.py`

- **"How do I create checks programmatically?"**  
  See `STAVES_QUICKSTART.md` → Creating Clefs section

---

**Everything is ready!** Start with:

```bash
cd datametronome/podium
cat STAVES_QUICKSTART.md
```

Happy monitoring! 🎵

