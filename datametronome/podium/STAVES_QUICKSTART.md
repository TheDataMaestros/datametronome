# 🎵 Staves & Clefs - Quick Start Guide

A clear, functional guide to working with Staves and Clefs in DataMetronome.

## What are Staves and Clefs?

- **Stave** = A data source you want to monitor (like a database, API, or file)
- **Clef** = A data quality check that runs against a Stave

Think of it like music: a stave is the staff where you write notes, and a clef tells you how to read them.

## 🚀 Quick Examples

### Creating a Stave

```python
from datametronome_podium.services.stave_service import create_postgres_stave

# Create a PostgreSQL stave
stave = create_postgres_stave(
    name="Production Database",
    host="db.example.com",
    database="prod_db",
    user="monitor_user",
    password="secure_password",
    description="Main production database"
)

print(stave)
# Output: 🟢 Active Production Database (postgres)
```

### Creating a Clef (Data Quality Check)

```python
from datametronome_podium.services.stave_service import create_null_check

# Create a check for NULL values
check = create_null_check(
    stave_id=stave.id,
    name="Email NULL Check",
    table="users",
    column="email",
    threshold=0.0,  # No NULLs allowed
    schedule="@hourly"  # Run every hour
)

print(check)
# Output: 🟢 Active Email NULL Check (null_check, scheduled: @hourly)
```

### Saving to Database

```python
from datametronome_podium.services.stave_service import serialize_stave

# Serialize for database storage
db_data = serialize_stave(stave)

# Now insert into database
await db.write([{
    "table": "staves",
    **db_data
}], "staves")
```

### Loading from Database

```python
from datametronome_podium.services.stave_service import deserialize_stave

# Query from database
rows = await db.query("SELECT * FROM staves WHERE id = ?", [stave_id])

# Deserialize back to Stave object
stave = deserialize_stave(rows[0])

# Now you can use it
print(f"Loaded: {stave.name}")
```

## 📚 Available Helper Functions

### Stave Creation

```python
from datametronome_podium.services.stave_service import (
    create_stave,           # Generic stave creation
    create_postgres_stave,  # PostgreSQL-specific
    create_sqlite_stave,    # SQLite-specific
    create_mysql_stave,     # MySQL-specific
)
```

### Clef (Check) Creation

```python
from datametronome_podium.services.stave_service import (
    create_clef,          # Generic check creation
    create_null_check,    # Check for NULL values
    create_range_check,   # Check value ranges
    create_volume_check,  # Check row counts
)
```

### Serialization

```python
from datametronome_podium.services.stave_service import (
    serialize_stave,      # Stave -> database format
    deserialize_stave,    # database -> Stave
    serialize_clef,       # Clef -> database format
    deserialize_clef,     # database -> Clef
)
```

### Utilities

```python
from datametronome_podium.services.stave_service import (
    generate_stave_id,           # Generate unique stave ID
    generate_clef_id,            # Generate unique clef ID
    is_valid_data_source_type,   # Check if type is supported
    is_valid_check_type,         # Check if check type is supported
)
```

## 🎯 Supported Data Sources

- `postgres` / `postgresql` - PostgreSQL databases
- `mysql` - MySQL databases
- `sqlite` - SQLite databases
- `mongodb` - MongoDB databases
- `redis` - Redis caches
- `snowflake` - Snowflake data warehouses
- `bigquery` - Google BigQuery
- `api` / `http` - HTTP APIs

## ✅ Supported Check Types

- `null_check` - Check for NULL values
- `uniqueness_check` - Check for duplicate values
- `range_check` - Check if values are within range
- `pattern_check` - Check if values match pattern/regex
- `freshness_check` - Check if data is recent
- `volume_check` - Check row count
- `custom_sql` - Custom SQL query
- `schema_check` - Validate schema hasn't changed
- `referential_check` - Check foreign key integrity

## 📖 Learn by Example

The best way to understand Staves and Clefs is to read the example tests:

```bash
# Run the example tests (they serve as documentation)
cd datametronome/podium
pytest tests/test_stave_examples.py -v

# Read the test file - it's full of examples!
cat tests/test_stave_examples.py
```

The test file contains:
- ✅ How to create different types of staves
- ✅ How to create different types of checks
- ✅ How to validate data
- ✅ How to serialize/deserialize
- ✅ Real-world scenarios

## 🔧 Common Patterns

### Pattern 1: Full Setup for a New Database

```python
# 1. Create the stave
stave = create_postgres_stave(
    name="Production User Database",
    host="prod-db.company.com",
    database="users_prod",
    user="monitor_readonly",
    password="secure_password"
)

# 2. Create checks
checks = [
    create_null_check(
        stave_id=stave.id,
        name="User Email Required",
        table="users",
        column="email",
        schedule="@hourly"
    ),
    create_range_check(
        stave_id=stave.id,
        name="User Age Range",
        table="users",
        column="age",
        min_value=0,
        max_value=150,
        schedule="@daily"
    ),
]

# 3. Save to database
stave_data = serialize_stave(stave)
checks_data = [serialize_clef(c) for c in checks]

await db.write([{"table": "staves", **stave_data}], "staves")
for check_data in checks_data:
    await db.write([{"table": "clefs", **check_data}], "clefs")
```

### Pattern 2: Load and Modify a Stave

```python
# Load from database
rows = await db.query("SELECT * FROM staves WHERE id = ?", [stave_id])
stave = deserialize_stave(rows[0])

# Modify
stave.description = "Updated description"
stave.is_active = False

# Save back
stave_data = serialize_stave(stave)
await db.write([{"table": "staves", **stave_data}], "staves")
```

### Pattern 3: Find All Checks for a Stave

```python
# Query all checks for a stave
rows = await db.query("SELECT * FROM clefs WHERE stave_id = ?", [stave_id])

# Deserialize them
checks = [deserialize_clef(row) for row in rows]

# Print summary
print(f"Found {len(checks)} checks:")
for check in checks:
    print(f"  - {check}")
```

## 🧪 Testing Your Code

When you write code that uses Staves, test it like this:

```python
def test_my_stave_feature():
    """Test my feature that uses staves."""
    # Create a test stave
    stave = create_sqlite_stave(
        name="Test DB",
        path="/tmp/test.db"
    )

    # Use it in your code
    result = my_function(stave)

    # Assert expected behavior
    assert result.is_active
```

## 🎓 Next Steps

1. **Read the examples**: `tests/test_stave_examples.py` is full of working examples
2. **Check the models**: `models/stave.py` and `models/clef.py` have detailed docstrings
3. **Explore the service**: `services/stave_service.py` has all the helper functions
4. **Build something**: Create a stave and some checks for your own database!

## 💡 Tips

- **Use helper functions**: `create_postgres_stave()` is easier than manual `Stave()` creation
- **IDs are auto-generated**: Don't worry about generating IDs yourself
- **Serialization is automatic**: Use `serialize_stave()` / `deserialize_stave()`
- **Types are case-insensitive**: "POSTGRES" and "postgres" both work
- **Tests are documentation**: Read `test_stave_examples.py` to learn

## 🐛 Common Issues

### Issue: "Unsupported data source type"
**Solution**: Check the supported types list above. Use lowercase: `postgres` not `POSTGRES`

### Issue: "connection_config cannot be empty"
**Solution**: You must provide at least one connection parameter

### Issue: "name cannot be empty or whitespace"
**Solution**: Provide a real name, not just spaces

### Issue: Database storage issues
**Solution**: Use `serialize_stave()` before saving, `deserialize_stave()` after loading

---

**Ready to build?** Start by running the examples:

```bash
pytest tests/test_stave_examples.py -v -s
```

Happy monitoring! 🎵
