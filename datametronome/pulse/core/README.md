# DataPulse Core

[![PyPI version](https://badge.fury.io/py/metronome-pulse-core.svg)](https://badge.fury.io/py/metronome-pulse-core)
[![Python versions](https://img.shields.io/pypi/pyversions/metronome-pulse-core.svg)](https://pypi.org/project/metronome-pulse-core/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Type checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](https://mypy-lang.org/)

**High-performance, async-first data connectivity framework for modern Python applications.**

DataPulse Core provides the foundational interfaces and abstractions that all DataPulse connectors implement. It's designed for building robust, scalable data pipelines with enterprise-grade reliability.

## ✨ Features

- **🔌 Universal Interface**: Consistent API across all database types
- **⚡ Async-First**: Built for high-performance, non-blocking operations
- **🛡️ Type Safe**: Full type hints and runtime validation
- **🔧 Extensible**: Easy to implement custom connectors
- **📊 Connection Pooling**: Efficient resource management
- **🔄 Transaction Support**: ACID compliance and rollback capabilities
- **📈 Performance Monitoring**: Built-in metrics and observability

## 🚀 Quick Start

### Installation

```bash
pip install metronome-pulse-core
```

### Basic Usage

```python
from metronome_pulse_core import Pulse, Readable, Writable
from typing import Any

class MyCustomConnector(Pulse, Readable, Writable):
    """Example custom connector implementation."""
    
    async def connect(self) -> None:
        """Establish connection to data source."""
        pass
    
    async def disconnect(self) -> None:
        """Close connection to data source."""
        pass
    
    async def is_connected(self) -> bool:
        """Check if connection is active."""
        return True
    
    async def query(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute read operation."""
        return []
    
    async def write(self, data: list[dict[str, Any]], config: dict[str, Any] | None = None) -> int:
        """Execute write operation."""
        return len(data)
```

## 📚 Core Interfaces

### `Pulse` - Base Interface
The foundation interface that all connectors must implement:

```python
class Pulse(ABC):
    """Base interface for all DataPulse connectors."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the data source."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the data source."""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if the connection is currently active."""
        pass
```

### `Readable` - Read Operations
Interface for data retrieval operations:

```python
class Readable(ABC):
    """Interface for read operations."""
    
    @abstractmethod
    async def query(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a query and return results."""
        pass
```

### `Writable` - Write Operations
Interface for data modification operations:

```python
class Writable(ABC):
    """Interface for write operations."""
    
    @abstractmethod
    async def write(self, data: list[dict[str, Any]], config: dict[str, Any] | None = None) -> int:
        """Write data using the specified configuration."""
        pass
```

## 🔧 Advanced Features

### Configuration-Driven Operations
All write operations support flexible configuration:

```python
# Simple insert
await connector.write(data, {"operation": "insert"})

# High-performance replace
await connector.write(data, {
    "operation": "replace",
    "batch_size": 1000,
    "use_transaction": True
})

# Custom SQL operations
await connector.write(data, {
    "operation": "custom",
    "sql_template": "INSERT INTO {table} ({columns}) VALUES {values}",
    "on_conflict": "DO NOTHING"
})
```

### Connection Pooling
Efficient resource management for high-throughput applications:

```python
from metronome_pulse_core import ConnectionPool

pool = ConnectionPool(
    connector_class=PostgresConnector,
    min_connections=5,
    max_connections=20,
    connection_timeout=30
)

async with pool.get_connection() as conn:
    result = await conn.query("SELECT * FROM users LIMIT 10")
```

## 🧪 Testing

### Run Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=metronome_pulse_core

# Run specific test categories
pytest -m "unit"
pytest -m "integration"
pytest -m "slow"
```

### Code Quality

```bash
# Format code
black metronome_pulse_core tests

# Sort imports
isort metronome_pulse_core tests

# Type checking
mypy metronome_pulse_core

# Linting
ruff check metronome_pulse_core tests
```

## 📦 Available Connectors

- **PostgreSQL**: `metronome-pulse-postgres` - High-performance async PostgreSQL
- **PostgreSQL (psycopg3)**: `metronome-pulse-postgres-psycopg3` - Modern psycopg3 driver
- **PostgreSQL (SQLAlchemy)**: `metronome-pulse-postgres-sqlalchemy` - SQLAlchemy integration
- **SQLite**: `metronome-pulse-sqlite` - Lightweight SQLite support
- **MongoDB**: `metronome-pulse-mongodb` - Document database support
- **Redis**: `metronome-pulse-redis` - In-memory data store

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/datametronome/metronome-pulse-core.git
cd metronome-pulse-core

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Documentation**: https://datametronome.dev/docs/pulse-core
- **Source Code**: https://github.com/datametronome/metronome-pulse-core
- **Issue Tracker**: https://github.com/datametronome/metronome-pulse-core/issues
- **PyPI Package**: https://pypi.org/project/metronome-pulse-core/

## 🙏 Acknowledgments

- Built with ❤️ by the DataMetronome team
- Inspired by modern async Python patterns
- Designed for enterprise data engineering workflows
