# DataMetronome YAML Import Guide

## 🎯 Quick Reference

### Import Demo Configuration

```bash
cd datametronome/podium

# Method 1: Using universal import utility (RECOMMENDED)
python3 scripts/import_yaml.py examples/demo-complete.yaml --clean

# Method 2: Using demo-specific script
python3 scripts/import_demo.py --clean

# Method 3: Automatic on first run
# Just delete DEMO staves and restart API - it auto-imports
sqlite3 datametronome.db "DELETE FROM staves WHERE name LIKE 'DEMO-%';"
# API auto-reloads and imports demo-complete.yaml
```

### Import Any YAML Configuration

```bash
cd datametronome/podium

# Dry run (preview what would be imported)
python3 scripts/import_yaml.py examples/your-config.yaml --dry-run

# Import without replacing existing
python3 scripts/import_yaml.py examples/your-config.yaml

# Clean import (replace existing items with matching IDs)
python3 scripts/import_yaml.py examples/your-config.yaml --clean
```

## 📦 What's Included

### Single Demo Configuration File

**`examples/demo-complete.yaml`** - Complete demo environment
- 2 Staves (Clickstream + E-commerce)
- 11 Clefs (NULL checks, volume, freshness, ML, drift detection)
- Auto-imported on first run

### Import Utilities

**`scripts/import_yaml.py`** - Universal YAML importer
- Works with any YAML file
- Supports --clean and --dry-run flags
- Comprehensive logging

**`scripts/import_demo.py`** - Demo-specific importer
- Specifically for demo-complete.yaml
- Includes cleanup option

## 📝 YAML File Structure

```yaml
staves:
  - id: stave-unique-id
    name: My Data Source
    description: What this data source is
    data_source_type: sqlite  # or postgres, mysql, etc.
    connection_config:
      database_path: my_data.db
    is_active: true

clefs:
  - id: clef-unique-id
    stave_id: stave-unique-id
    name: My Quality Check
    description: What this check does
    check_type: column_values
    config:
      table: my_table
      column: my_column
      condition: if_null
    warn: "if_null > 5%"
    fail: "if_null > 20%"
    schedule: "@hourly"
    is_active: true
```

## 🔄 Complete Workflow Example

### 1. Clean Existing Demo Data

```bash
cd datametronome/podium
python3 scripts/import_yaml.py examples/demo-complete.yaml --clean
```

### 2. Verify Import

```bash
# Check what was created
sqlite3 datametronome.db "SELECT id, name FROM staves WHERE name LIKE 'DEMO-%';"
sqlite3 datametronome.db "SELECT id, name, schedule FROM clefs;"
```

### 3. Restart API (if needed)

The API auto-reloads with `--reload` flag. If not running with reload:

```bash
# Stop current API (Ctrl+C)
# Start with environment variables
export DATAMETRONOME_SECRET_KEY="demo-secret-key"
export DATAMETRONOME_DEBUG="true"
export DATAMETRONOME_PORT="8001"
python3 -m datametronome_podium.main
```

### 4. Open Dashboard

```bash
# In another terminal, start the dashboard server
cd /Users/totolasso/repos/personal/datametronome
python3 -m http.server 3000
```

Open browser: http://localhost:3000/dashboard.html

### 5. Generate Sample Data

In the dashboard:
1. Go to **Overview** tab
2. Select a stave (DEMO-Clickstream or DEMO-Ecommerce)
3. Select a table (clicks, users, orders, products)
4. Click "✨ Generate Data"
5. Watch the checks run!

## 🎯 Import Utility Features

### Universal Import (`import_yaml.py`)

**Supports:**
- ✅ Any YAML file with staves/clefs
- ✅ Dry run mode to preview
- ✅ Clean mode to replace existing
- ✅ Detailed logging
- ✅ Error handling
- ✅ Summary statistics

**Command Line:**
```bash
python3 scripts/import_yaml.py <yaml_file> [--clean] [--dry-run]
```

**Output Example:**
```
📂 Loading configuration from examples/demo-complete.yaml
📊 Found in YAML:
  - Staves: 2
  - Clefs: 11

📊 Creating 2 staves...
  ✅ DEMO-Clickstream (ID: stave-demo-clickstream)
  ✅ DEMO-Ecommerce (ID: stave-demo-ecommerce)

🎯 Creating 11 clefs...
  ✅ Clicks NULL Value Check [*/2 * * * *]
  ✅ Clickstream Volume Check [@hourly]
  ... (9 more)

🎉 Configuration imported successfully!

📊 Summary:
  - Staves created: 2
  - Clefs created: 11
```

## 🗂️ File Organization

```
examples/
├── README.md                    # This file
├── README_DEMO_IMPORT.md       # Detailed demo import guide
├── demo-complete.yaml          # ⭐ Main demo configuration
├── tdd-compliant-clefs.yaml    # TDD examples
├── tiered-checks-examples.yaml # Tiered checks examples
├── conflicting-config.yaml     # Validation examples
├── staves.yaml                 # Template
└── production-db.yaml          # Production template
```

## 💡 Tips

1. **Always use --dry-run first** to preview what will be imported
2. **Use --clean carefully** - it deletes existing data with matching IDs
3. **Keep your YAML files in version control** for history
4. **Start with demo-complete.yaml** as a template for your own configs
5. **Use descriptive IDs and names** for easier management

## 🆘 Troubleshooting

**Import fails:**
- Check YAML syntax: `python3 -c "import yaml; yaml.safe_load(open('your-file.yaml'))"`
- Verify file path is correct
- Check database permissions

**Clefs not scheduling:**
- Restart the API after importing
- Check logs for scheduling errors
- Verify cron expressions are valid

**Stave connection fails:**
- Test connection in dashboard
- Verify connection_config is correct
- Check database is accessible

## 📚 More Information

- **Main README**: `datametronome/podium/README.md`
- **API Documentation**: http://localhost:8001/docs
- **Dashboard**: http://localhost:3000/dashboard.html

---

**Need help?** Check the documentation or open an issue on GitHub.
