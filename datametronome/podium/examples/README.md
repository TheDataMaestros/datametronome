# DataMetronome YAML Configuration Examples

This directory contains example YAML configurations for staves (data sources) and clefs (quality checks).

## 📁 Files Overview

### Demo Configurations

#### `demo-complete.yaml` ⭐ **RECOMMENDED FOR DEMOS**
Complete demo environment with 2 staves and 11 clefs. This is the **single source of truth** for demo configurations.

**Contains:**
- 2 Staves: DEMO-Clickstream, DEMO-Ecommerce
- 11 Clefs: Comprehensive quality checks including NULL checks, volume checks, freshness checks, ML anomaly detection, and data drift detection

**Auto-imported on first run** by the Podium API.

### Documentation Examples

#### `tdd-compliant-clefs.yaml`
Demonstrates TDD-compliant clef configurations following the official design document.

#### `tiered-checks-examples.yaml`
Shows the four tiers of data quality checks (Level 1-4) with severity configurations.

#### `conflicting-config.yaml`
Example showing configuration conflicts and validation errors (for testing).

### Template Examples

#### `staves.yaml`
Template for defining data sources in YAML format.

#### `production-db.yaml`
Example production database configuration.

## 🚀 Quick Start

### Import Demo Configuration

**Option 1: Automatic (First Run)**
```bash
cd datametronome/podium
export DATAMETRONOME_SECRET_KEY="your-secret-key"
export DATAMETRONOME_DEBUG="true"
export DATAMETRONOME_PORT="8001"
python3 -m datametronome_podium.main
```

The API will automatically import `demo-complete.yaml` on first run.

**Option 2: Manual Import**
```bash
cd datametronome/podium
python3 scripts/import_yaml.py examples/demo-complete.yaml
```

**Option 3: Clean Import (Replace Existing)**
```bash
cd datametronome/podium
python3 scripts/import_yaml.py examples/demo-complete.yaml --clean
```

**Option 4: Dry Run (Preview)**
```bash
cd datametronome/podium
python3 scripts/import_yaml.py examples/demo-complete.yaml --dry-run
```

## 📝 YAML Format

### Basic Structure

```yaml
staves:
  - id: stave-my-database
    name: My Database
    description: Description of the data source
    data_source_type: sqlite  # or postgres, mysql, etc.
    connection_config:
      database_path: my_data.db  # SQLite
      # OR for PostgreSQL:
      # host: localhost
      # port: 5432
      # database: mydb
      # user: myuser
      # password: mypass
    is_active: true

clefs:
  - id: clef-my-check
    stave_id: stave-my-database
    name: My Quality Check
    description: Description of what this check does
    check_type: column_values  # or row_count, freshness, etc.
    config:
      table: my_table
      column: my_column
      condition: if_null
    warn: "if_null > 5%"   # Optional warning threshold
    fail: "if_null > 20%"  # Optional failure threshold
    schedule: "@hourly"    # Cron expression or @hourly, @daily, etc.
    is_active: true
```

### Supported Check Types

- `row_count` - Check total number of rows
- `freshness` - Check data freshness (time since last update)
- `column_values` - Validate values within a column (NULL checks, range checks, etc.)
- `forecast` - ML-driven anomaly detection
- `data_profile_drift` - Statistical drift detection
- `lookup_validation` - Cross-system integrity validation
- `python` - Custom Python script

### Schedule Formats

- Cron expressions: `"*/5 * * * *"` (every 5 minutes)
- Shortcuts: `"@hourly"`, `"@daily"`, `"@weekly"`, `"@monthly"`
- Specific times: `"0 9 * * *"` (9 AM daily)

## 🛠️ Import Utility

### Universal YAML Import Script

`scripts/import_yaml.py` - Can import **any** YAML file with staves/clefs.

**Usage:**
```bash
python3 scripts/import_yaml.py <yaml_file> [options]
```

**Options:**
- `--clean` - Delete existing items with matching IDs before importing
- `--dry-run` - Preview what would be imported without actually importing
- `--help` - Show help message

**Examples:**
```bash
# Preview what would be imported
python3 scripts/import_yaml.py examples/demo-complete.yaml --dry-run

# Import new configuration
python3 scripts/import_yaml.py examples/my-config.yaml

# Replace existing configuration
python3 scripts/import_yaml.py examples/demo-complete.yaml --clean

# Import production configuration
python3 scripts/import_yaml.py examples/production-db.yaml
```

## 🔄 Workflow

### 1. Create Your Configuration

Create a YAML file with your staves and clefs:

```bash
cp examples/demo-complete.yaml examples/my-config.yaml
# Edit my-config.yaml with your configuration
```

### 2. Validate (Dry Run)

```bash
python3 scripts/import_yaml.py examples/my-config.yaml --dry-run
```

### 3. Import

```bash
python3 scripts/import_yaml.py examples/my-config.yaml
```

### 4. Restart API

The API will auto-reload if running with `--reload` flag, or manually restart:

```bash
python3 -m datametronome_podium.main
```

### 5. Verify

Check the dashboard or use the API:

```bash
# Via API
curl http://localhost:8001/api/v1/staves/ -H "Authorization: Bearer YOUR_TOKEN"
curl http://localhost:8001/api/v1/clefs/ -H "Authorization: Bearer YOUR_TOKEN"

# Via database
sqlite3 datametronome.db "SELECT id, name FROM staves;"
sqlite3 datametronome.db "SELECT id, name, schedule FROM clefs;"
```

## 🎯 Best Practices

1. **Use descriptive IDs** - Makes it easier to reference and debug
2. **Add descriptions** - Document what each check does
3. **Start with demo** - Use `demo-complete.yaml` as a template
4. **Version control** - Keep YAML files in git for history
5. **Test with dry-run** - Always preview before importing
6. **Use --clean carefully** - It deletes existing data!

## 📚 Documentation

- **`README_DEMO_IMPORT.md`** - Detailed guide for demo configuration
- **`DEMO_README.md`** - General demo information
- **API Docs** - http://localhost:8001/docs

## 🆘 Troubleshooting

### Import fails with "stave_id not found"
Make sure staves are defined before clefs in the YAML file, or that the stave_id exists in the database.

### Clefs not scheduling
Restart the API after importing to trigger scheduler initialization.

### Duplicate IDs
Use `--clean` flag to replace existing items, or change the IDs in your YAML file.

### YAML syntax errors
Validate your YAML syntax using a YAML validator or `python3 -c "import yaml; yaml.safe_load(open('your-file.yaml'))"`

## 🎵 Happy Monitoring!

For more information, see the main DataMetronome documentation.

