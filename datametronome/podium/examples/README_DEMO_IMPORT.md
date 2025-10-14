# Demo Configuration Import Guide

## 📦 Complete Demo Configuration

The `demo-complete.yaml` file contains everything you need for a full DataMetronome demonstration:

- **2 Staves**: Clickstream and E-commerce databases
- **11 Clefs**: Comprehensive quality checks including NULL checks, volume checks, freshness checks, and ML-based anomaly detection

## 🚀 Automatic Import (First Run)

The demo configuration is **automatically imported** when you start the Podium API for the first time:

```bash
cd datametronome/podium

# Set required environment variables
export DATAMETRONOME_SECRET_KEY="demo-secret-key-for-development-only"
export DATAMETRONOME_DEBUG="true"
export DATAMETRONOME_PORT="8001"

# Start the API
python3 -m datametronome_podium.main
```

**What happens:**
1. API starts and initializes database
2. Checks if DEMO staves already exist
3. If not found, loads `demo-complete.yaml`
4. Creates all staves and clefs from the YAML
5. Sets up database tables
6. Schedules clefs to run automatically

You'll see logs like:
```
2025-10-09 23:03:29 - INFO - Loading demo configuration from demo-complete.yaml
2025-10-09 23:03:29 - INFO - ✅ Created stave: DEMO-Clickstream
2025-10-09 23:03:29 - INFO - ✅ Created stave: DEMO-Ecommerce
2025-10-09 23:03:29 - INFO - ✅ Created clef: Clicks NULL Value Check
2025-10-09 23:03:29 - INFO - ✅ Demo configuration loaded from YAML
```

## 🔄 Manual Import/Reimport

### Method 1: Using the Import Script

```bash
cd datametronome/podium
python3 scripts/import_staves.py examples/demo-complete.yaml
```

### Method 2: Delete and Restart (Clean Slate)

To reimport the configuration from scratch:

```bash
cd datametronome/podium

# 1. Delete existing demo data
sqlite3 datametronome.db "DELETE FROM checks WHERE stave_id IN (SELECT id FROM staves WHERE name LIKE 'DEMO-%');"
sqlite3 datametronome.db "DELETE FROM clefs WHERE stave_id IN (SELECT id FROM staves WHERE name LIKE 'DEMO-%');"
sqlite3 datametronome.db "DELETE FROM staves WHERE name LIKE 'DEMO-%';"

# 2. Restart the API (it will auto-reload with --reload flag)
# Or manually restart:
# python3 -m datametronome_podium.main
```

The API will detect that DEMO staves don't exist and automatically import from `demo-complete.yaml`.

### Method 3: Python Script

Create a script to import programmatically:

```python
import asyncio
import yaml
from datametronome_podium.core.database import get_db
from datametronome_podium.services.stave_service import (
    create_stave, serialize_stave, 
    create_clef, serialize_clef
)

async def import_demo_config():
    """Import demo configuration from YAML."""
    with open('examples/demo-complete.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    db = await get_db()
    
    # Create staves
    for stave_config in config['staves']:
        stave = create_stave(
            name=stave_config['name'],
            data_source_type=stave_config['data_source_type'],
            connection_config=stave_config['connection_config'],
            description=stave_config.get('description')
        )
        if 'id' in stave_config:
            stave.id = stave_config['id']
        
        await db.write([serialize_stave(stave)], "staves")
        print(f"✅ Created stave: {stave.name}")
    
    # Create clefs
    for clef_config in config['clefs']:
        clef = create_clef(
            stave_id=clef_config['stave_id'],
            name=clef_config['name'],
            check_type=clef_config['check_type'],
            config=clef_config['config'],
            description=clef_config.get('description'),
            schedule=clef_config.get('schedule'),
            is_active=clef_config.get('is_active', True),
            warn=clef_config.get('warn'),
            fail=clef_config.get('fail')
        )
        if 'id' in clef_config:
            clef.id = clef_config['id']
        
        await db.write([serialize_clef(clef)], "clefs")
        print(f"✅ Created clef: {clef.name}")
    
    print("✅ Demo configuration imported successfully!")

# Run the import
asyncio.run(import_demo_config())
```

Save as `scripts/import_demo.py` and run:
```bash
cd datametronome/podium
python3 scripts/import_demo.py
```

## 📋 What Gets Created

### Staves (2)
1. **DEMO-Clickstream** - For web analytics data
2. **DEMO-Ecommerce** - For e-commerce data (users, products, orders)

### Clefs (11)

#### Clickstream Monitoring (3 clefs)
- ✅ **Clicks NULL Value Check** - Runs every 2 minutes
- ✅ **Clickstream Volume Check** - Runs hourly
- ✅ **Clickstream Data Freshness** - Runs hourly

#### E-commerce Monitoring (6 clefs)
- ✅ **Users Email Check** - NULL validation, runs hourly
- ✅ **Users Table Volume** - Row count check, runs hourly
- ✅ **Product Price Validation** - Price validation, runs hourly
- ⚠️ **Products Availability Check** - Ensures catalog not empty, runs hourly
- ✅ **Orders Volume Check** - Order count monitoring, runs daily
- ✅ **Orders Data Freshness** - Recent orders check, runs daily

#### Advanced Analytics (2 clefs)
- 🤖 **ML Anomaly Detection** - Machine learning based, runs daily
- 📊 **Data Drift Detection** - Statistical drift detection, runs daily

## 🎯 Quick Start

### Option 1: Fresh Start (Recommended)

```bash
# 1. Navigate to podium directory
cd datametronome/podium

# 2. Clear any existing demo data
sqlite3 datametronome.db "DELETE FROM checks WHERE stave_id IN (SELECT id FROM staves WHERE name LIKE 'DEMO-%');"
sqlite3 datametronome.db "DELETE FROM clefs WHERE stave_id IN (SELECT id FROM staves WHERE name LIKE 'DEMO-%');"
sqlite3 datametronome.db "DELETE FROM staves WHERE name LIKE 'DEMO-%';"

# 3. Start the API (it will auto-import demo-complete.yaml)
export DATAMETRONOME_SECRET_KEY="demo-secret-key-for-development-only"
export DATAMETRONOME_DEBUG="true"
export DATAMETRONOME_PORT="8001"
python3 -m datametronome_podium.main
```

### Option 2: Keep Existing Data

If you want to keep your existing data and just add the demo configuration, use the import script (Method 1 or 3 above).

## 📊 Generating Sample Data

Once imported, use the dashboard to generate sample data:

1. Open dashboard: http://localhost:3000/dashboard.html
2. Go to **Overview** tab
3. Use the **Monitored Data Preview** section:
   - Select a stave (DEMO-Clickstream or DEMO-Ecommerce)
   - Select a table (clicks, users, orders, products)
   - Click "✨ Generate Data" if table is empty
4. Or go to **Staves** tab and click on a stave to generate data

## 🔧 Customization

Edit `demo-complete.yaml` to:
- Add more clefs
- Change schedules
- Adjust warn/fail thresholds
- Add descriptions
- Enable/disable checks

After editing, reimport using the methods above.

## 📁 File Location

```
datametronome/podium/examples/demo-complete.yaml
```

## ✅ Verification

After import, verify everything is set up:

```bash
# Check staves
sqlite3 datametronome.db "SELECT id, name FROM staves WHERE name LIKE 'DEMO-%';"

# Check clefs
sqlite3 datametronome.db "SELECT id, name, schedule FROM clefs WHERE stave_id IN (SELECT id FROM staves WHERE name LIKE 'DEMO-%');"

# Or use the API
curl http://localhost:8001/api/v1/staves/ -H "Authorization: Bearer YOUR_TOKEN"
curl http://localhost:8001/api/v1/clefs/ -H "Authorization: Bearer YOUR_TOKEN"
```

## 🎵 Next Steps

1. **Generate sample data** for all tables
2. **Watch the checks run** automatically based on their schedules
3. **View results** in the dashboard
4. **Explore the UI** - click on staves/clefs to see YAML configs
5. **Run checks manually** using the "▶️ Run" button

Your DataMetronome demo environment is now fully configured and ready to showcase! 🎉

