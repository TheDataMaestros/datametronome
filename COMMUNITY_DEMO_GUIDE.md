# 🎵 DataMetronome Community Demo Guide

Welcome to the DataMetronome Community Demo! This guide will help you get the complete ecosystem running and showcase all the amazing features.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ (tested with 3.11, 3.12, 3.13)
- Docker and Docker Compose (optional, for full showcase)
- Git

### 🎯 **Current Status** 
✅ **All services are working and accessible via browser!**

- **Podium API**: Running on http://localhost:8001
- **API Documentation**: http://localhost:8001/docs  
- **UI**: Running on http://localhost:3000
- **Login Credentials**: `admin` / `admin`

### 1. Clone and Setup
```bash
git clone <repository-url>
cd datametronome
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies
```bash
# Install core packages
cd datametronome/pulse/sqlite && uv pip install -e .
cd ../postgres && uv pip install -e .
cd ../core && uv pip install -e .
cd ../../podium && uv pip install -e .

# Install development dependencies
uv pip install pytest pytest-asyncio black isort mypy
```

### 3. Run the Community Demo
```bash
python3 community_demo.py
```

## 🎯 What the Demo Shows

The community demo showcases the complete DataMetronome ecosystem with both **command-line testing** and **browser interfaces**:

### ✅ SQLite DataPulse Connector
- High-performance async SQLite connectivity
- In-memory database testing
- Basic query execution
- Connection management

### ✅ PostgreSQL DataPulse Connector  
- Enterprise-grade PostgreSQL connectivity
- Connection pooling with asyncpg
- Version detection and health checks
- Production-ready configuration

### ✅ Data Quality Monitoring
- Row count validation
- Data freshness checks
- Schema validation
- Anomaly detection simulation

### ✅ Anomaly Detection
- Statistical outlier detection
- Schema change monitoring
- Data freshness alerts
- Severity-based classification

### ✅ Reporting System
- System health scoring
- Check execution metrics
- Anomaly summary reporting
- Real-time status updates

### ✅ UI Integration
- Modern web-based interface at http://localhost:8501
- Real-time data visualization and dashboards
- Configuration management for staves and clefs
- Interactive anomaly detection results
- Data exploration and investigation tools
- Report generation and download

### ✅ Podium API
- RESTful API endpoints at http://localhost:8001
- Interactive API documentation at http://localhost:8001/docs
- JWT authentication (admin/admin)
- Prometheus metrics at http://localhost:8001/metrics
- Health monitoring at http://localhost:8001/health

## 🐳 Full Showcase with Docker

For the complete showcase experience with real PostgreSQL database:

### 1. Start PostgreSQL Database
```bash
docker-compose up -d postgres
```

### 2. Wait for Database Ready
```bash
# Wait about 15 seconds for PostgreSQL to initialize
sleep 15
```

### 3. Run Enhanced Demo
```bash
python3 community_demo.py
```

Now you'll see:
- ✅ **SQLite Connector**: Working with in-memory database
- ✅ **PostgreSQL Connector**: Connected to real PostgreSQL 15 database
- ✅ **All other components**: Fully functional

### 4. Start Full Services
```bash
# Start Podium API (backend)
source .venv/bin/activate
cd datametronome/podium
DATAMETRONOME_SECRET_KEY="dev-secret-key-change-in-production-32-chars" DATAMETRONOME_DATABASE_URL="sqlite+aiosqlite:///$(pwd)/data/datametronome.db" python -m datametronome_podium.main

# In another terminal, start the UI
source .venv/bin/activate
cd ui-nuxt
npm install
npm run dev -- --port 3000 --host
```

**Or use the automated setup:**
```bash
# Start services automatically
./run_showcase.sh
```

Access the services:
- 🚀 **Podium API**: http://localhost:8001
- 📚 **API Docs**: http://localhost:8001/docs
- 🎨 **UI**: http://localhost:3000
- 🔑 **Login**: admin / admin

## 📊 Demo Results

When everything is working, you should see:

```
🎵 DataMetronome Community Demo
============================================================
🚀 Testing the complete DataMetronome ecosystem...

🔌 SQLite DataPulse Connector Demo
✅ Connected to SQLite database
✅ Available tables: []
✅ Basic query test: [{'test': 1}]
✅ SQLite connector is operational

🔌 PostgreSQL DataPulse Connector Demo  
✅ Connected to PostgreSQL database
✅ PostgreSQL version: PostgreSQL 15.14 (Debian 15.14-1.pgdg13+1)...

🔍 Data Quality Monitoring Demo
✅ row_count: Row count within expected range
✅ freshness: Data is fresh (last update: 2 hours ago)
✅ schema: Schema validation successful
✅ anomaly_detection: No statistical anomalies detected

🚨 Anomaly Detection Demo
⚠️ outlier - medium
🚨 schema_change - high
⚠️ data_freshness - low

📊 Reporting Demo
📈 System Health Summary:
   Overall Score: 87.5%
   Total Checks: 24
   Passed: 21 ✅
   Failed: 3 ❌

🎨 UI Demo
✅ UI frontend available

🚀 Podium API Demo
✅ Podium API package available
✅ Podium API configuration validated

============================================================
📊 Demo Results Summary
✅ PASS SQLite Connector
✅ PASS PostgreSQL Connector  
✅ PASS Data Quality Monitoring
✅ PASS Anomaly Detection
✅ PASS Reporting
✅ PASS UI
✅ PASS Podium API

🎯 Overall: 7/7 demos passed
🎉 All demos completed successfully!
```

## 🛠️ Troubleshooting

### PostgreSQL Connection Issues
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Package Import Issues
```bash
# Reinstall packages
cd datametronome/pulse/sqlite && uv pip install -e .
cd ../postgres && uv pip install -e .
cd ../core && uv pip install -e .
cd ../../podium && uv pip install -e .
```

### Services Not Starting
```bash
# Check if services are running
curl http://localhost:8001/health  # Podium API
curl http://localhost:3000         # UI

# Restart services manually
pkill -f "datametronome_podium"    # Kill Podium API
pkill -f "nuxt"                    # Kill UI (Nuxt process)

# Then restart using the commands in section 4
```

### Environment Issues
```bash
# Ensure you're using the virtual environment
source .venv/bin/activate
which python3  # Should point to .venv/bin/python3
```

## 🎉 Next Steps

After running the community demo:

### 🌐 **Browser Exploration:**
1. **API Documentation**: Visit http://localhost:8001/docs
   - Test authentication with `admin`/`admin`
   - Explore all API endpoints
   - Try creating staves and clefs

2. **Dashboard UI**: Visit http://localhost:3000
   - Login with `admin`/`admin`
   - Explore all dashboard tabs
   - Run data quality checks
   - View anomaly detection results

### 🚀 **Advanced Usage:**
3. **Run Realistic Demo**: `python3 demo_realistic.py`
4. **Test with PostgreSQL**: Use the showcase script `./run_showcase.sh`
5. **Read Documentation**: Check the `docs/` directory
6. **Join the Community**: Contribute to the project!

## 📚 Additional Resources

- **API Documentation**: `docs/api.md`
- **Architecture Overview**: `docs/architecture.md`
- **Development Guide**: `docs/development.md`
- **TDD Alignment**: `docs/TDD_DataPulse.md`

## 🤝 Contributing

We welcome contributions! Check out:
- `CONTRIBUTING.md` - How to contribute
- `CODE RULE CLUB` - Our development standards
- Issue tracker for bugs and feature requests

---

**🎵 DataMetronome Community Demo - Making Data Quality Musical! 🎵**
