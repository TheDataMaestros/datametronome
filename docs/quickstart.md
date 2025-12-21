# 🚀 DataMetronome Quick Start Guide

Welcome to DataMetronome! This guide will help you get started based on your role and use case.

---

## 📋 Choose Your Path

- [🔧 For Data Engineers](#-for-data-engineers) - Monitor data pipelines and quality
- [⚙️ For DevOps Teams](#%EF%B8%8F-for-devops-teams) - Deploy and monitor infrastructure
- [🔬 For Data Scientists](#-for-data-scientists) - Ensure data quality for ML models
- [👨‍💻 For Developers](#-for-developers) - Integrate DataMetronome into your apps

---

## 🔧 For Data Engineers

**Goal**: Monitor your data pipelines and catch quality issues early.

### Quick Start (5 minutes)

1. **Install DataMetronome:**
   ```bash
   pip install metronome-pulse-postgres
   # or for other databases:
   pip install metronome-pulse-sqlite
   ```

2. **Connect to your database:**
   ```python
   import asyncio
   from metronome_pulse_postgres import PostgresConnector

   async def check_data_quality():
       # Connect to your PostgreSQL database
       connector = PostgresConnector(
           host="localhost",
           port=5432,
           database="your_db",
           user="your_user",
           password="your_password"
       )

       await connector.connect()

       # Check for NULL values in critical columns
       nulls = await connector.read(
           "SELECT COUNT(*) FROM users WHERE email IS NULL"
       )
       print(f"Found {nulls[0][0]} users with NULL emails")

       await connector.disconnect()

   asyncio.run(check_data_quality())
   ```

3. **Set up anomaly detection:**
   ```python
   # Check for unusual patterns in your data
   from metronome_pulse_postgres import PostgresConnector
   import pandas as pd
   from sklearn.ensemble import IsolationForest

   async def detect_anomalies():
       connector = PostgresConnector(
           host="localhost",
           database="your_db",
           user="your_user",
           password="your_password"
       )

       await connector.connect()

       # Get recent order amounts
       query = """
           SELECT order_amount, created_at
           FROM orders
           WHERE created_at > NOW() - INTERVAL '7 days'
       """
       results = await connector.read(query)

       # Convert to DataFrame
       df = pd.DataFrame(results, columns=['amount', 'created_at'])

       # Detect anomalies using Isolation Forest
       model = IsolationForest(contamination=0.1)
       df['anomaly'] = model.fit_predict(df[['amount']])

       # Show anomalies
       anomalies = df[df['anomaly'] == -1]
       print(f"Found {len(anomalies)} anomalous orders:")
       print(anomalies)

       await connector.disconnect()

   asyncio.run(detect_anomalies())
   ```

### Next Steps

- 📊 [Launch the UI](#launch-the-dashboard) for visual monitoring
- 🔔 [Set up alerts](#set-up-alerts) for critical data quality issues
- 📈 [View API Documentation](api.md) for advanced queries

---

## ⚙️ For DevOps Teams

**Goal**: Deploy DataMetronome and monitor data infrastructure health.

### Quick Deployment (10 minutes)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/datametronome/datametronome.git
   cd datametronome
   ```

2. **Start with Docker Compose:**
   ```bash
   # Copy environment example
   cp env.example .env

   # Edit .env with your settings
   nano .env

   # Start all services
   docker-compose up -d
   ```

3. **Access the services:**
   - 🎯 **Podium API**: http://localhost:8000
   - 📚 **API Docs**: http://localhost:8000/docs
   - 📊 **UI**: http://localhost:3000 (run via `npm run dev --prefix ui-nuxt`)
   - 🗄️ **PostgreSQL**: localhost:5432

4. **Verify health:**
   ```bash
   # Check API health
   curl http://localhost:8000/health

   # Check all services
   docker-compose ps

   # View logs
   docker-compose logs -f
   ```

### Production Deployment

For production deployment, see our detailed [Deployment Guide](../DEPLOYMENT.md) which covers:

- 🐳 Docker production setup
- ☸️ Kubernetes deployment
- 🔒 Security best practices
- 📊 Monitoring and observability
- 🔄 Scaling strategies

### Monitoring Setup

1. **Enable Prometheus metrics** (coming in Q4 2024):
   ```yaml
   # docker-compose.yml
   services:
     podium:
       environment:
         - ENABLE_METRICS=true
   ```

2. **View metrics:**
   ```bash
   curl http://localhost:8000/metrics
   ```

3. **Set up Grafana dashboards** (templates coming soon)

---

## 🔬 For Data Scientists

**Goal**: Ensure data quality for ML models and detect data drift.

### Quick Start (5 minutes)

1. **Install DataMetronome:**
   ```bash
   pip install metronome-pulse-postgres
   pip install scikit-learn pandas
   ```

2. **Profile your training data:**
   ```python
   import asyncio
   from metronome_pulse_postgres import PostgresConnector
   import pandas as pd

   async def profile_data():
       connector = PostgresConnector(
           host="localhost",
           database="ml_db",
           user="ml_user",
           password="password"
       )

       await connector.connect()

       # Get training dataset
       query = "SELECT * FROM training_data WHERE dataset = 'v1'"
       results = await connector.read(query)

       # Convert to DataFrame for analysis
       df = pd.DataFrame(results)

       # Get comprehensive statistics
       print("Dataset Profile:")
       print(f"Rows: {len(df)}")
       print(f"Columns: {len(df.columns)}")
       print(f"\nMissing Values:")
       print(df.isnull().sum())
       print(f"\nStatistics:")
       print(df.describe())

       await connector.disconnect()

   asyncio.run(profile_data())
   ```

3. **Detect data drift:**
   ```python
   from sklearn.ensemble import IsolationForest
   import pandas as pd

   async def detect_drift():
       connector = PostgresConnector(
           host="localhost",
           database="ml_db",
           user="ml_user",
           password="password"
       )

       await connector.connect()

       # Compare training vs production distributions
       train_query = "SELECT feature_1, feature_2 FROM training_data"
       prod_query = "SELECT feature_1, feature_2 FROM production_data WHERE created_at > NOW() - INTERVAL '1 day'"

       train_data = await connector.read(train_query)
       prod_data = await connector.read(prod_query)

       train_df = pd.DataFrame(train_data, columns=['f1', 'f2'])
       prod_df = pd.DataFrame(prod_data, columns=['f1', 'f2'])

       # Train on training data
       model = IsolationForest(contamination=0.05)
       model.fit(train_df)

       # Detect anomalies in production data
       prod_df['drift'] = model.predict(prod_df)
       drift_pct = (prod_df['drift'] == -1).mean() * 100

       print(f"Data drift detected: {drift_pct:.2f}% of production data is anomalous")
       if drift_pct > 10:
           print("⚠️  WARNING: Significant data drift detected!")
           print("Consider retraining your model.")

       await connector.disconnect()

   asyncio.run(detect_drift())
   ```

### Automated Monitoring (YAML)

Instead of writing scripts, you can define drift and forecast checks declaratively using YAML. This enables continuous, automated monitoring without maintaining custom code:

```yaml
# data/staves/ml_monitoring.yaml
name: "ML Data Quality"
data_source_type: "postgres"
connection_config:
  host: "localhost"
  database: "ml_db"
schedule: "0 * * * *"  # Run hourly

checks:
  # Level 2: Time-series Forecasting (SARIMA)
  # Automatically detects anomalies based on historical patterns
  - type: forecast
    name: "order_volume_anomaly"
    config:
      # Query should return timestamp and value columns
      query: "SELECT created_at, amount FROM orders WHERE created_at > NOW() - INTERVAL '30 days'"
      timestamp_column: "created_at"
      value_column: "amount"

  # Level 2: Data Drift Detection (Kolmogorov-Smirnov)
  # Detects if the distribution of new data differs from baseline
  - type: data_profile_drift
    name: "feature_drift_check"
    config:
      table: "model_features"
      column: "input_variable_x"
      # Compare last 24h against historical baseline
      baseline_condition: "created_at BETWEEN NOW() - INTERVAL '30 days' AND NOW() - INTERVAL '1 day'"
      current_condition: "created_at > NOW() - INTERVAL '1 day'"
      critical_p_value: 0.05  # Alert if distributions differ significantly
```

### Advanced Features

- 🤖 [ML-Powered Anomaly Detection](api.md#ml-anomaly-detection)
- 📊 [Statistical Analysis Tools](api.md#statistical-analysis)
- 📈 [Time Series Analysis](api.md#time-series)

---

## 👨‍💻 For Developers

**Goal**: Integrate DataMetronome into your applications.

### Installation

```bash
# Install specific connector
pip install metronome-pulse-postgres  # PostgreSQL (asyncpg)
pip install metronome-pulse-postgres-psycopg3  # PostgreSQL (psycopg3)
pip install metronome-pulse-postgres-sqlalchemy  # PostgreSQL (SQLAlchemy)
pip install metronome-pulse-sqlite  # SQLite

# Or install from source
git clone https://github.com/datametronome/datametronome.git
cd datametronome
pip install -e ./datametronome/pulse/core
pip install -e ./datametronome/pulse/postgres
```

### Basic Usage

#### Read Operations

```python
import asyncio
from metronome_pulse_postgres import PostgresConnector

async def read_example():
    connector = PostgresConnector(
        host="localhost",
        port=5432,
        database="mydb",
        user="user",
        password="password"
    )

    await connector.connect()

    # Simple query
    results = await connector.read("SELECT * FROM users LIMIT 10")
    for row in results:
        print(row)

    # Parameterized query
    results = await connector.read(
        "SELECT * FROM users WHERE age > $1",
        params=[25]
    )

    await connector.disconnect()

asyncio.run(read_example())
```

#### Write Operations

```python
async def write_example():
    connector = PostgresConnector(
        host="localhost",
        database="mydb",
        user="user",
        password="password"
    )

    await connector.connect()

    # Insert data
    await connector.write(
        "INSERT INTO users (name, email, age) VALUES ($1, $2, $3)",
        params=["Alice", "alice@example.com", 30]
    )

    # Batch insert
    users = [
        ("Bob", "bob@example.com", 25),
        ("Charlie", "charlie@example.com", 35),
    ]

    for name, email, age in users:
        await connector.write(
            "INSERT INTO users (name, email, age) VALUES ($1, $2, $3)",
            params=[name, email, age]
        )

    await connector.disconnect()

asyncio.run(write_example())
```

#### Using Context Managers

```python
async def context_manager_example():
    async with PostgresConnector(
        host="localhost",
        database="mydb",
        user="user",
        password="password"
    ) as connector:
        # Connection is automatically managed
        results = await connector.read("SELECT COUNT(*) FROM users")
        count = results[0][0]
        print(f"Total users: {count}")
    # Connection is automatically closed
```

### API Integration

If you're using the Podium API:

```python
import httpx

# API base URL
API_BASE = "http://localhost:8000"

async def api_example():
    async with httpx.AsyncClient() as client:
        # Create a stave (data source configuration)
        stave_data = {
            "name": "Production DB",
            "type": "postgres",
            "config": {
                "host": "prod-db.example.com",
                "port": 5432,
                "database": "prod"
            }
        }

        response = await client.post(
            f"{API_BASE}/api/v1/staves",
            json=stave_data
        )
        stave = response.json()
        print(f"Created stave: {stave['id']}")

        # Create a check (data quality rule)
        check_data = {
            "stave_id": stave["id"],
            "name": "Check for NULL emails",
            "type": "null_check",
            "config": {
                "table": "users",
                "column": "email"
            }
        }

        response = await client.post(
            f"{API_BASE}/api/v1/clefs",
            json=check_data
        )
        check = response.json()
        print(f"Created check: {check['id']}")

asyncio.run(api_example())
```

### Retail Demo with Historical Data

The retail demo automatically generates historical check results when you import the configuration. This provides rich visualizations showing:

- **Data Drift**: Gradual distribution shift over multiple days (not just a single outlier)
- **Forecast Anomalies**: Historical normal behavior vs. today's anomaly
- **Trend Analysis**: Baseline patterns and threshold visualization

To set up the full demo with historical data:

```bash
# Generate retail database
make retail-db

# Import configuration (automatically generates historical checks)
export DB_PATH="$(pwd)/datametronome/podium/data/retail.db"
python3 showcase/retail_demo/import_to_podium.py

# Start API and UI, then view graphs in the Quality Checks page
```

### Advanced Topics

- 📚 [Full API Reference](api.md)
- 🏗️ [Architecture Overview](architecture.md)
- 🔧 [Development Guide](development.md)

---

## 🎨 Launch the Dashboard

For all users, the UI dashboard provides a beautiful visual interface:

### Installation

```bash
# Clone the repository
git clone https://github.com/datametronome/datametronome.git
cd datametronome

# Install UI dependencies
cd ui-nuxt
npm install
```

### Launch

```bash
# Start the UI in dev mode (defaults to http://localhost:3000)
npm run dev
```

The dashboard will open at **http://localhost:3000** with:

- 📊 **Overview Tab** - Real-time system health and data quality scores
- 🚨 **Anomalies Tab** - Live anomaly detection and alerts
- 🤖 **ML Anomalies Tab** - Machine learning-powered outlier detection
- 📈 **Trends & Patterns Tab** - Time series analysis and correlations
- 🔍 **Investigation Tab** - Custom SQL queries and data profiling

---

## 🔔 Set Up Alerts

**Note**: Alert system coming in Q4 2024. For now, you can build custom alerts:

```python
async def simple_alert():
    connector = PostgresConnector(...)
    await connector.connect()

    # Check for critical condition
    result = await connector.read(
        "SELECT COUNT(*) FROM orders WHERE amount < 0"
    )

    negative_count = result[0][0]

    if negative_count > 0:
        # Send alert (integrate with your notification system)
        print(f"🚨 ALERT: {negative_count} orders with negative amounts!")
        # TODO: Send email, Slack message, etc.

    await connector.disconnect()
```

---

## 📚 Next Steps

Now that you're up and running:

1. 📖 **Read the Documentation**
   - [API Reference](api.md) - Complete API documentation
   - [Architecture Guide](architecture.md) - System design and components
   - [Development Guide](development.md) - Contributing to DataMetronome

2. 🎯 **Explore Examples**
   - [Example Scripts](../examples/) - Real-world use cases
   - [Community Demo](../community_demo.py) - Full demonstration

3. 🤝 **Join the Community**
   - ⭐ Star us on [GitHub](https://github.com/datametronome/datametronome)
   - 💬 Join discussions
   - 🐛 Report issues and request features

4. 🚀 **Deploy to Production**
   - [Deployment Guide](../DEPLOYMENT.md) - Production deployment strategies
   - [Security Best Practices](../DEPLOYMENT.md#security)
   - [Scaling Guide](../DEPLOYMENT.md#scaling)

---

## ❓ Troubleshooting

### Connection Issues

```python
# Test database connectivity
import asyncio
from metronome_pulse_postgres import PostgresConnector

async def test_connection():
    try:
        connector = PostgresConnector(
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
            password="testpass"
        )
        await connector.connect()
        print("✅ Connection successful!")
        await connector.disconnect()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test_connection())
```

### Common Issues

1. **"Module not found" error**
   ```bash
   # Make sure you've installed the package
   pip install metronome-pulse-postgres
   ```

2. **Database connection timeout**
   ```python
   # Increase timeout in connection parameters
   connector = PostgresConnector(
       host="localhost",
       database="mydb",
       user="user",
       password="password",
       timeout=30  # seconds
   )
   ```

3. **SSL/TLS connection issues**
   ```python
   # For SSL connections
   connector = PostgresConnector(
       host="secure-db.example.com",
       database="mydb",
       user="user",
       password="password",
       ssl="require"  # or "prefer", "disable"
   )
   ```

### Getting Help

- 📖 Check the [full documentation](api.md)
- 🐛 [Open an issue](https://github.com/datametronome/datametronome/issues)
- 💬 Ask in [GitHub Discussions](https://github.com/datametronome/datametronome/discussions)
- 📧 Email: support@datametronome.dev

---

**🎵 Happy monitoring with DataMetronome!**

*Questions or feedback? We'd love to hear from you!*
