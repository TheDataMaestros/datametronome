# DataPulse BigQuery

[![PyPI version](https://badge.fury.io/py/metronome-pulse-bigquery.svg)](https://badge.fury.io/py/metronome-pulse-bigquery)
[![Python versions](https://img.shields.io/pypi/pyversions/metronome-pulse-bigquery.svg)](https://pypi.org/project/metronome-pulse-bigquery/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**High-performance, async-first Google BigQuery connector for the DataPulse ecosystem.**

DataPulse BigQuery provides enterprise-grade connectivity to Google BigQuery with support for complex queries, data quality checks, and seamless integration with the DataMetronome platform.

## ✨ Features

- **⚡ Async-First**: Built with asyncio for non-blocking operations
- **🔐 Secure Authentication**: Support for service account credentials
- **📊 Full Query Support**: Execute complex SQL queries with parameters
- **🔄 Read & Write Operations**: Complete data pipeline support
- **🛡️ Type Safe**: Full type hints and runtime validation
- **📈 Optimized Performance**: Efficient connection management
- **🌍 Multi-Region**: Support for any BigQuery location (US, EU, etc.)
- **📋 Schema Inspection**: Get table metadata and schema information

## 🚀 Quick Start

### Installation

```bash
pip install metronome-pulse-bigquery
```

### Basic Usage

```python
import asyncio
from metronome_pulse_bigquery import BigQueryPulse

async def main():
    # Initialize connector
    pulse = BigQueryPulse(
        project_id="my-gcp-project",
        credentials_path="/path/to/service-account.json",
        dataset="my_dataset"
    )

    # Connect to BigQuery
    await pulse.connect()

    # Execute a query
    results = await pulse.query("SELECT * FROM users LIMIT 10")
    print(f"Found {len(results)} users")

    # Write data
    data = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"}
    ]
    await pulse.write(data, "users")

    # Get table information
    schema = await pulse.get_table_info("users")
    print(f"Table schema: {schema}")

    # Close connection
    await pulse.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Read-Only Access

For data quality checks and monitoring, use the read-only connector:

```python
from metronome_pulse_bigquery import BigQueryReadonlyPulse

async def check_data_quality():
    # Initialize read-only connector
    pulse = BigQueryReadonlyPulse(
        project_id="my-gcp-project",
        credentials_path="/path/to/service-account.json"
    )

    await pulse.connect()

    # Safe read operations only
    results = await pulse.query({
        "sql": "SELECT COUNT(*) as count FROM dataset.users WHERE created_at > @date",
        "params": ["2024-01-01"]
    })

    await pulse.close()
```

## 🔧 Configuration

### Authentication Methods

**Service Account File:**
```python
pulse = BigQueryPulse(
    project_id="my-project",
    credentials_path="/path/to/service-account.json"
)
```

**Service Account JSON:**
```python
pulse = BigQueryPulse(
    project_id="my-project",
    credentials_json={
        "type": "service_account",
        "project_id": "my-project",
        # ... other credentials
    }
)
```

### Advanced Configuration

```python
pulse = BigQueryPulse(
    project_id="my-project",
    credentials_path="/path/to/credentials.json",
    dataset="analytics",           # Default dataset
    location="EU",                  # BigQuery location
)
```

## 📊 DataMetronome Integration

### Stave Configuration (YAML)

```yaml
staves:
  - id: stave-bigquery-analytics
    name: BigQuery Analytics
    description: Production analytics database
    data_source_type: bigquery
    connection_config:
      project_id: my-gcp-project
      credentials_path: /path/to/service-account.json
      dataset: analytics
      location: US
    is_active: true
```

### Stave Configuration (Python)

```python
from datametronome_podium.models import Stave

stave = Stave(
    id="stave-bigquery-001",
    name="BigQuery Analytics",
    data_source_type="bigquery",
    connection_config={
        "project_id": "my-gcp-project",
        "credentials_path": "/path/to/service-account.json",
        "dataset": "analytics"
    }
)
```

## 🔍 Query Examples

### Simple Query
```python
results = await pulse.query("SELECT * FROM users LIMIT 100")
```

### Parameterized Query
```python
results = await pulse.query({
    "sql": "SELECT * FROM users WHERE status = @status",
    "params": ["active"]
})
```

### Table Information
```python
# Get schema
schema = await pulse.get_table_info("users")

# List tables in dataset
tables = await pulse.list_tables("analytics")
```

## 📝 Write Operations

### Insert Data
```python
data = [
    {"user_id": 1, "action": "login", "timestamp": "2024-01-01T10:00:00"},
    {"user_id": 2, "action": "logout", "timestamp": "2024-01-01T11:00:00"}
]
await pulse.write(data, "user_events")
```

### Replace Data
```python
await pulse.write(
    data,
    "user_events",
    config={"mode": "replace"}  # Truncate and insert
)
```

## 🧪 Testing

```bash
# Install dev dependencies
pip install metronome-pulse-bigquery[dev]

# Run tests
pytest tests/
```

## 📚 API Reference

### BigQueryPulse

Main connector class implementing Pulse, Readable, and Writable interfaces.

**Methods:**
- `connect()`: Establish connection
- `close()`: Close connection
- `is_connected()`: Check connection status
- `query(query_config)`: Execute query
- `write(data, destination, config)`: Write data
- `get_table_info(table_name)`: Get table schema
- `list_tables(dataset)`: List tables in dataset

### BigQueryReadonlyPulse

Read-only connector for safe data access.

**Methods:**
- `connect()`: Establish connection
- `close()`: Close connection
- `is_connected()`: Check connection status
- `query(query_config)`: Execute read-only query
- `get_table_info(table_name)`: Get table schema
- `list_tables(dataset)`: List tables in dataset

## 🔒 Security Best Practices

1. **Use Service Accounts**: Create dedicated service accounts with minimal permissions
2. **Credential Storage**: Store credentials securely, never commit to version control
3. **Read-Only Access**: Use `BigQueryReadonlyPulse` for monitoring and checks
4. **IAM Permissions**: Grant only necessary BigQuery permissions
5. **Environment Variables**: Use environment variables for sensitive data

## 🤝 Contributing

Contributions are welcome! Please see the main DataMetronome repository for contribution guidelines.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- [DataMetronome Documentation](https://github.com/datametronome/datametronome)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [PyPI Package](https://pypi.org/project/metronome-pulse-bigquery/)

## 🆘 Support

For issues, questions, or contributions:
- GitHub Issues: [datametronome/datametronome](https://github.com/datametronome/datametronome/issues)
- Email: team@datametronome.dev
