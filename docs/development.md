# 👨‍💻 DataMetronome Development Guide

Complete guide for contributing to DataMetronome development.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [CODE RULE CLUB](#code-rule-club)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Contributing](#contributing)

---

## Getting Started

### Prerequisites

- **Python 3.11+** (project tests on 3.11, 3.12, 3.13)
- **Git** for version control
- **Docker & Docker Compose** (optional, for testing)
- **PostgreSQL 15+** (optional, for integration tests)
- **uv** or **pip** for package management

### Fork and Clone

```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/datametronome.git
cd datametronome

# Add upstream remote
git remote add upstream https://github.com/datametronome/datametronome.git
```

---

## Development Environment Setup

### Option 1: Local Development (Recommended)

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install all pulse packages in development mode
pip install -e ./datametronome/pulse/core
pip install -e ./datametronome/pulse/postgres
pip install -e ./datametronome/pulse/postgres-psycopg3
pip install -e ./datametronome/pulse/postgres-sqlalchemy
pip install -e ./datametronome/pulse/sqlite

# Install podium
pip install -e ./datametronome/podium

# Install UI dependencies
npm install --prefix ui-nuxt

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock
pip install black isort flake8 mypy
pip install pre-commit
```

### Option 2: Using uv (Faster)

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install packages
uv pip install -e ./datametronome/pulse/core
uv pip install -e ./datametronome/pulse/postgres
# ... repeat for other packages

# Install dev dependencies
uv pip install pytest pytest-asyncio pytest-cov black isort flake8 mypy
```

### Option 3: Docker Development

```bash
# Start all services
docker-compose up -d

# Access running containers
docker-compose exec podium bash

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Setup Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Project Structure

```
datametronome/
├── datametronome/           # Main source code
│   ├── brain/              # Analytics and profiling (internal)
│   │   └── base/
│   ├── podium/             # FastAPI backend (application)
│   │   ├── datametronome_podium/
│   │   │   ├── api/        # API endpoints
│   │   │   ├── core/       # Core configuration
│   │   │   ├── models/     # Pydantic models
│   │   │   └── services/   # Business logic
│   │   └── tests/          # Podium tests
│   ├── pulse/              # DataPulse connectors (PyPI packages)
│   │   ├── core/           # Base interfaces
│   │   ├── postgres/       # PostgreSQL (asyncpg)
│   │   ├── postgres-psycopg3/  # PostgreSQL (psycopg3)
│   │   ├── postgres-sqlalchemy/  # PostgreSQL (SQLAlchemy)
│   │   └── sqlite/         # SQLite connector
│   └── ui-nuxt/            # UI dashboard (application)
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── tests/                  # End-to-end tests
├── .github/workflows/      # CI/CD pipelines
└── docker-compose.yml      # Docker configuration
```

### Package Types

Following [PACKAGE_STRUCTURE.md](../datametronome/PACKAGE_STRUCTURE.md):

**PyPI Packages** (can be `pip install`ed):
- `pulse/core/`
- `pulse/postgres/`
- `pulse/postgres-psycopg3/`
- `pulse/postgres-sqlalchemy/`
- `pulse/sqlite/`

**Applications** (run standalone):
- `podium/` - FastAPI backend
- `ui-nuxt/` - UI dashboard

**Internal** (not distributed):
- `brain/base/` - Internal utilities

---

## CODE RULE CLUB

DataMetronome follows **CODE RULE CLUB** principles (our coding standards):

### 1. **Unit Tests First** 
Unit tests are **MOST IMPORTANT** and must pass before anything else.

```python
# Good: Clear, focused unit test
def test_user_email_validation():
    """Test that invalid emails are rejected."""
    with pytest.raises(ValidationError):
        User(username="test", email="invalid-email")
```

### 2. **Integration Tests with Proper Database Setup**
Integration tests must use real database instances to test:
- Partitions (weekly, daily, monthly)
- All CRUD operations
- Transaction handling

```python
@pytest.fixture
async def postgres_db():
    """Provide a real PostgreSQL database for testing."""
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=os.getenv("POSTGRES_DB", "testdb"),
        user=os.getenv("POSTGRES_USER", "testuser"),
        password=os.getenv("POSTGRES_PASSWORD", "testpass")
    )
    yield conn
    await conn.close()
```

### 3. **Built-in Type Hints**
Use Python's built-in type hint syntax (no `typing` module imports when possible):

```python
# Good: Built-in types
def process_data(items: list[dict[str, int]]) -> tuple[int, int]:
    ...

# Avoid: Importing from typing
from typing import List, Dict, Tuple
def process_data(items: List[Dict[str, int]]) -> Tuple[int, int]:
    ...
```

### 4. **Asyncpg for Database Interactions**
Use asyncpg for PostgreSQL and Pydantic models (no SQLAlchemy in core):

```python
# Good: asyncpg + Pydantic
from pydantic import BaseModel

class User(BaseModel):
    id: int
    username: str
    email: str

async def get_user(conn, user_id: int) -> User:
    row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    return User(**row)
```

### 5. **CI Tests on Python 3.11, 3.12, 3.13**
All code must pass tests on these three versions.

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

Follow the coding standards:
- Write clear, descriptive commit messages
- Add tests for new functionality
- Update documentation as needed
- Follow PEP 8 style guide

### 3. Test Your Changes

```bash
# Run unit tests
pytest tests/test_unit.py -v

# Run all tests
pytest -v

# With coverage
pytest --cov=datametronome_podium --cov-report=term-missing
```

### 4. Format and Lint

```bash
# Format code
black datametronome/
isort datametronome/

# Lint
flake8 datametronome/
mypy datametronome/ --ignore-missing-imports
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "feat: add new anomaly detection algorithm

- Implemented LSTM-based detection
- Added tests for time series data
- Updated documentation"
```

**Commit Message Format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a PR on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots (if UI changes)
- Test results

---

## Testing

### Test Organization

```
tests/
├── test_unit.py           # Unit tests (run first, most important)
├── test_integration_database.py  # Integration tests with DB
└── test_api_integration.py      # API integration tests
```

### Running Tests

```bash
# Unit tests only (fastest)
cd datametronome/podium
pytest tests/test_unit.py -v

# Integration tests (requires database)
export POSTGRES_HOST=localhost
export POSTGRES_DB=testdb
export POSTGRES_USER=testuser
export POSTGRES_PASSWORD=testpass
pytest tests/test_integration_database.py -v

# All tests
pytest tests/ -v

# Specific test
pytest tests/test_unit.py::TestUserModel::test_user_creation -v

# With coverage
pytest tests/ --cov=datametronome_podium --cov-report=html
```

### Writing Tests

#### Unit Test Example

```python
import pytest
from pydantic import ValidationError
from datametronome_podium.models.user import User

class TestUserModel:
    """Unit tests for User model."""
    
    def test_user_creation_valid_data(self):
        """Test creating user with valid data."""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
    
    def test_user_validation_invalid_email(self):
        """Test that invalid email raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            User(
                username="testuser",
                email="not-an-email",
                full_name="Test"
            )
        assert "email" in str(exc_info.value)
```

#### Integration Test Example

```python
import pytest
import asyncpg

@pytest.fixture
async def db_connection():
    """Provide database connection."""
    conn = await asyncpg.connect(
        host="localhost",
        database="testdb",
        user="testuser",
        password="testpass"
    )
    
    # Setup: create test table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS test_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100),
            email VARCHAR(255)
        )
    """)
    
    yield conn
    
    # Teardown: clean up
    await conn.execute("DROP TABLE test_users")
    await conn.close()

@pytest.mark.asyncio
async def test_user_crud_operations(db_connection):
    """Test complete CRUD cycle."""
    # Create
    user_id = await db_connection.fetchval(
        "INSERT INTO test_users (username, email) VALUES ($1, $2) RETURNING id",
        "testuser", "test@example.com"
    )
    assert user_id is not None
    
    # Read
    user = await db_connection.fetchrow(
        "SELECT * FROM test_users WHERE id = $1",
        user_id
    )
    assert user["username"] == "testuser"
    
    # Update
    await db_connection.execute(
        "UPDATE test_users SET email = $1 WHERE id = $2",
        "new@example.com", user_id
    )
    
    # Verify update
    updated = await db_connection.fetchrow(
        "SELECT email FROM test_users WHERE id = $1",
        user_id
    )
    assert updated["email"] == "new@example.com"
    
    # Delete
    await db_connection.execute(
        "DELETE FROM test_users WHERE id = $1",
        user_id
    )
    
    # Verify deletion
    deleted = await db_connection.fetchrow(
        "SELECT * FROM test_users WHERE id = $1",
        user_id
    )
    assert deleted is None
```

### Test Database Setup

```bash
# Using Docker
docker run -d \
  --name postgres-test \
  -e POSTGRES_DB=testdb \
  -e POSTGRES_USER=testuser \
  -e POSTGRES_PASSWORD=testpass \
  -p 5432:5432 \
  postgres:15

# Or use docker-compose
docker-compose -f docker-compose.test.yml up -d
```

---

## Code Quality

### Code Formatting

We use **Black** for consistent formatting:

```bash
# Format all code
black datametronome/

# Check without modifying
black --check datametronome/

# Format specific file
black datametronome/podium/models/user.py
```

### Import Sorting

We use **isort** for organized imports:

```bash
# Sort imports
isort datametronome/

# Check only
isort --check-only datametronome/
```

### Linting

We use **flake8** for linting:

```bash
# Lint all code
flake8 datametronome/

# With specific rules
flake8 datametronome/ --max-line-length=100 --ignore=E203,W503
```

### Type Checking

We use **mypy** for static type checking:

```bash
# Type check
mypy datametronome/ --ignore-missing-imports

# Strict mode
mypy datametronome/ --strict
```

### Pre-commit Configuration

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

---

## Contributing

### Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes** (with tests!)
4. **Run the full test suite**
5. **Update documentation**
6. **Submit PR** with clear description

### PR Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Code formatted (`black datametronome/`)
- [ ] Imports sorted (`isort datametronome/`)
- [ ] Linting passes (`flake8 datametronome/`)
- [ ] Type hints added
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Commit messages follow convention

### Code Review Process

1. **Automated checks** run via GitHub Actions
2. **Code review** by maintainers
3. **Feedback** addressed in follow-up commits
4. **Approval** and merge by maintainers

---

## Development Tips

### Debugging

```python
# Use breakpoint() for debugging
async def my_function():
    result = await some_async_call()
    breakpoint()  # Execution pauses here
    return result

# Or use logging
import logging
logger = logging.getLogger(__name__)

async def my_function():
    logger.debug(f"Processing {len(items)} items")
    ...
```

### Working with Async Code

```python
# Run async function in sync context
import asyncio

async def my_async_function():
    return await some_operation()

# In script or REPL
result = asyncio.run(my_async_function())

# In Jupyter notebook
await my_async_function()
```

### Testing Database Migrations

```bash
# Create test database
createdb datametronome_test

# Run migrations
python scripts/migrate_database.py

# Test
pytest tests/test_integration_database.py

# Cleanup
dropdb datametronome_test
```

---

## Building Packages

### For Local Testing

```bash
cd datametronome/pulse/postgres
python -m build
pip install dist/metronome_pulse_postgres-*.whl
```

### For PyPI (Maintainers Only)

```bash
# Build
python -m build

# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ metronome-pulse-postgres

# Upload to PyPI
python -m twine upload dist/*
```

---

## Getting Help

- 📖 Read the [documentation](quickstart.md)
- 💬 Ask in [GitHub Discussions](https://github.com/datametronome/datametronome/discussions)
- 🐛 Report bugs in [Issues](https://github.com/datametronome/datametronome/issues)
- 📧 Email: dev@datametronome.dev

---

## Resources

- [Quick Start](quickstart.md)
- [API Reference](api.md)
- [Architecture](architecture.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [CODE RULE CLUB](../datametronome/PACKAGE_STRUCTURE.md)

---

**Happy coding! 🎵**

*Thanks for contributing to DataMetronome!*

