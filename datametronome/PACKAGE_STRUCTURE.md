# DataMetronome Package Structure

This document explains which directories in the DataMetronome project are PyPI packages vs. standalone applications or internal infrastructure.

## 🚀 PyPI Packages (Published to pip)

These are Python libraries that can be installed via `pip install`:

### Core Libraries
- **`pulse/core/`** - `metronome-pulse-core` - Core DataPulse functionality
- **`pulse/postgres/`** - `metronome-pulse-postgres` - PostgreSQL connector
- **`pulse/sqlite/`** - `metronome-pulse-sqlite` - SQLite connector

### Database Adapters
- **`pulse/postgres-sqlalchemy/`** - `metronome-pulse-postgres-sqlalchemy` - SQLAlchemy-based PostgreSQL
- **`pulse/postgres-psycopg3/`** - `metronome-pulse-postgres-psycopg3` - psycopg3-based PostgreSQL

## 🏠 Standalone Applications (NOT PyPI Packages)

These are complete applications that run independently:

### Backend Services
- **`podium/`** - FastAPI backend service for data quality monitoring
  - Provides REST API endpoints
  - Runs as a standalone service
  - Not meant to be imported as a library

### Frontend Applications
- **`ui-streamlit/`** - Streamlit-based user interface
  - Complete web application
  - Communicates with podium backend
  - Not meant to be installed via pip

## 🔧 Internal Infrastructure (NOT PyPI Packages)

These are internal components not meant for external use:

### Core Infrastructure
- **`brain/base/`** - Internal analytics and profiling code
  - Used by other DataMetronome components
  - Not meant for external consumption
  - May be refactored into public packages later

### Other Infrastructure
- **`plugins/`** - Plugin system components
- **`docs/`** - Documentation and guides
- **`scripts/`** - Utility scripts and tools
- **`tests/`** - Test suites and test data

## 📦 Package Management

### For PyPI Packages
```bash
# Build and publish
cd pulse/postgres
python -m build
python -m twine upload dist/*

# Install in development
pip install -e .
```

### For Applications
```bash
# Run directly
cd podium
python -m datametronome_podium.main

cd ui-streamlit
streamlit run datametronome_ui_streamlit/main.py
```

### For Infrastructure
```bash
# Install dependencies only
cd brain/base
pip install -r requirements.txt  # if exists
```

## 🚫 Preventing Accidental PyPI Publishing

Each non-PyPI directory contains:
- `.pypi-ignore` file with clear warnings
- README with directory type indicators
- No `setup.py` or `pyproject.toml` (where appropriate)
- `.gitignore` entries to prevent package artifacts

## 🔄 Future Considerations

- **`brain/base/`** might become a public package if there's demand
- **`podium/`** could be containerized and distributed via Docker
- **`ui-streamlit/`** could be distributed as a standalone executable

---

**Remember**: Only the `pulse/*` directories are meant to be PyPI packages. Everything else is either a standalone application or internal infrastructure.

