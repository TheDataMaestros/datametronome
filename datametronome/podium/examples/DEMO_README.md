# DataMetronome Demo Configurations

This directory contains demo configurations for showcasing the DataMetronome podium system and Streamlit UI.

## 🎵 Quick Start

### 1. Setup Demo Environment
```bash
cd datametronome/podium
python3 scripts/setup_demo_environment.py
```

### 2. Load Demo Configurations
```bash
python3 scripts/load_demo_configs.py
```

### 3. Import into Database
```bash
python3 -m datametronome_podium.scripts.import_staves examples/demo-simple-monitoring.yaml
```

## 📊 Demo Configurations

### `demo-simple-monitoring.yaml`
**Perfect for quick testing and demonstrations**
- 2 staves (SQLite + PostgreSQL)
- 4 basic clefs (Level 1: Declarative)
- Simple checks: NULL validation, row count, freshness

### `demo-streamlit-ui.yaml`
**Designed to showcase all UI features and severity levels**
- 1 stave (PostgreSQL)
- 8 clefs across all levels (1, 2, 4)
- Shows Harmony ✅, Dissonance ⚠️, and Cacophony ❌ states
- Perfect for UI demonstrations

### `demo-ecommerce-monitoring.yaml`
**Realistic e-commerce monitoring setup**
- 4 staves (PostgreSQL, Redis, MongoDB)
- 14 clefs across all 4 levels
- Complete monitoring for users, orders, products, inventory
- Production-ready configuration

## 🎼 Check Types Demonstrated

### Level 1: Simple Declarative Checks
- `column_values` - NULL checks, range validation, pattern matching
- `row_count` - Volume monitoring
- `freshness` - Data staleness detection

### Level 2: Intelligent Checks (ML-Driven)
- `forecast` - Anomaly detection using SARIMA
- `data_profile_drift` - Statistical drift detection

### Level 3: Advanced Declarative Checks
- `lookup_validation` - Cross-source reconciliation

### Level 4: Custom Code
- `python` - Custom business logic validation

## 🎯 Severity Levels

### Harmony ✅ (Pass)
- All checks within acceptable thresholds
- Data is healthy and behaving as expected

### Dissonance ⚠️ (Warning)
- Non-critical issues detected
- Data is still usable but requires attention

### Cacophony ❌ (Failure)
- Critical issues that require immediate attention
- Business-impacting problems

## 🔧 Environment Variables

The demo configurations use environment variables for flexibility:

```bash
# Demo Database
DEMO_HOST=localhost
DEMO_PORT=5432
DEMO_DB=streamlit_demo
DEMO_USER=demo
DEMO_PASSWORD=demo123

# Production Demo (e-commerce)
PROD_DB_HOST=localhost
PROD_DB_NAME=ecommerce_prod
# ... etc
```

## 📈 Sample Data

The setup script creates:
- **SQLite Database** (`/tmp/demo.db`):
  - 12 users (2 with NULL emails for testing)
  - 10 products
  - 50 orders
- **Sample Check Results** (`sample_check_results.json`)
- **Environment File** (`demo.env`)

## 🚀 Integration with Streamlit UI

These configurations are designed to work seamlessly with the Streamlit UI:

1. **Visualization**: See all staves and clefs in the UI
2. **Status Monitoring**: Real-time severity level display
3. **Configuration Management**: Import/export configurations
4. **Results Display**: View check execution results

## 💡 Demo Tips

1. **Start Simple**: Use `demo-simple-monitoring.yaml` first
2. **Show Severity Levels**: Use `demo-streamlit-ui.yaml` for UI demos
3. **Production Example**: Use `demo-ecommerce-monitoring.yaml` for realistic scenarios
4. **Custom Checks**: Modify the Python scripts in Level 4 checks
5. **Environment**: Use the provided environment variables or modify as needed

## 🎵 TDD Compliance

All configurations are fully TDD-compliant:
- ✅ Uses only supported check types
- ✅ Proper `warn` and `fail` condition syntax
- ✅ Correct severity mapping (pass/warn/fail → Harmony/Dissonance/Cacophony)
- ✅ All 4 levels of checks represented
- ✅ Comprehensive validation and conflict detection

Happy monitoring! 🎼
