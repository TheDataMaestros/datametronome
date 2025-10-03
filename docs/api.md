# 📚 DataMetronome API Reference

Complete API documentation for DataMetronome components.

---

## Table of Contents

- [DataPulse Connectors API](#datapulse-connectors-api)
- [Podium REST API](#podium-rest-api)
- [Python Client Library](#python-client-library)
- [Authentication](#authentication)
- [Error Handling](#error-handling)

---

## DataPulse Connectors API

DataPulse connectors provide high-performance, async-first database connectivity.

### PostgreSQL Connector (asyncpg)

**Package**: `metronome-pulse-postgres`

#### Installation

```bash
pip install metronome-pulse-postgres
```

#### Basic Usage

```python
from metronome_pulse_postgres import PostgresConnector

connector = PostgresConnector(
    host="localhost",
    port=5432,
    database="mydb",
    user="user",
    password="password",
    # Optional parameters
    min_pool_size=10,
    max_pool_size=20,
    timeout=30,
    command_timeout=60
)
```

#### Connection Management

```python
# Manual connection management
await connector.connect()
# ... perform operations ...
await connector.disconnect()

# Context manager (recommended)
async with PostgresConnector(...) as conn:
    results = await conn.read("SELECT * FROM users")
```

#### Read Operations

```python
# Simple query
results = await connector.read("SELECT * FROM users")
# Returns: list[tuple]

# Parameterized query
results = await connector.read(
    "SELECT * FROM users WHERE age > $1 AND city = $2",
    params=[25, "New York"]
)

# Query with options
results = await connector.read(
    query="SELECT * FROM users",
    fetch_size=1000,  # For large result sets
    timeout=30
)
```

####  Write Operations

```python
# Insert
await connector.write(
    "INSERT INTO users (name, email) VALUES ($1, $2)",
    params=["Alice", "alice@example.com"]
)

# Update
await connector.write(
    "UPDATE users SET last_login = $1 WHERE id = $2",
    params=[datetime.now(), 123]
)

# Delete
await connector.write(
    "DELETE FROM users WHERE inactive_days > $1",
    params=[365]
)
```

#### Batch Operations

```python
# Batch insert
users_data = [
    ("Alice", "alice@example.com", 30),
    ("Bob", "bob@example.com", 25),
    ("Charlie", "charlie@example.com", 35)
]

for name, email, age in users_data:
    await connector.write(
        "INSERT INTO users (name, email, age) VALUES ($1, $2, $3)",
        params=[name, email, age]
    )

# Or use executemany (if available)
await connector.batch_write(
    "INSERT INTO users (name, email, age) VALUES ($1, $2, $3)",
    params_list=users_data
)
```

#### Transactions

```python
async with connector.transaction() as tx:
    await connector.write(
        "INSERT INTO orders (user_id, amount) VALUES ($1, $2)",
        params=[user_id, 100.00]
    )
    await connector.write(
        "UPDATE users SET balance = balance - $1 WHERE id = $2",
        params=[100.00, user_id]
    )
    # Transaction commits automatically if no exception
    # Rolls back on exception
```

### PostgreSQL Connector (psycopg3)

**Package**: `metronome-pulse-postgres-psycopg3`

Similar API to asyncpg connector, with psycopg3-specific features:

```python
from metronome_pulse_postgres_psycopg3 import Psycopg3Connector

connector = Psycopg3Connector(
    host="localhost",
    database="mydb",
    user="user",
    password="password"
)
```

### PostgreSQL Connector (SQLAlchemy)

**Package**: `metronome-pulse-postgres-sqlalchemy`

ORM-based connector with SQLAlchemy:

```python
from metronome_pulse_postgres_sqlalchemy import SQLAlchemyConnector

connector = SQLAlchemyConnector(
    connection_string="postgresql+asyncpg://user:pass@localhost/mydb"
)

# Use with SQLAlchemy models
from sqlalchemy import select
from your_models import User

async with connector.session() as session:
    result = await session.execute(select(User).where(User.age > 25))
    users = result.scalars().all()
```

### SQLite Connector

**Package**: `metronome-pulse-sqlite`

```python
from metronome_pulse_sqlite import SQLiteConnector

connector = SQLiteConnector(
    database_path="./data/mydb.sqlite",
    check_same_thread=False  # For async usage
)

# Same read/write API as PostgreSQL connectors
await connector.connect()
results = await connector.read("SELECT * FROM users")
await connector.disconnect()
```

---

## Podium REST API

The Podium API provides REST endpoints for managing data quality monitoring.

### Base URL

```
http://localhost:8000
```

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Authentication

All endpoints (except `/health` and `/login`) require JWT authentication.

#### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "your_password"
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

#### Using the Token

```http
GET /api/v1/staves
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Staves (Data Sources)

#### List All Staves

```http
GET /api/v1/staves
Authorization: Bearer {token}
```

Response:
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Production Database",
    "type": "postgres",
    "config": {
      "host": "db.example.com",
      "port": 5432,
      "database": "prod"
    },
    "created_at": "2024-10-01T10:00:00Z",
    "updated_at": "2024-10-01T10:00:00Z"
  }
]
```

#### Create a Stave

```http
POST /api/v1/staves
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Production Database",
  "type": "postgres",
  "config": {
    "host": "db.example.com",
    "port": 5432,
    "database": "prod",
    "user": "monitor_user"
  }
}
```

#### Get a Stave

```http
GET /api/v1/staves/{stave_id}
Authorization: Bearer {token}
```

#### Update a Stave

```http
PUT /api/v1/staves/{stave_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Updated Name",
  "config": {
    "host": "new-db.example.com"
  }
}
```

#### Delete a Stave

```http
DELETE /api/v1/staves/{stave_id}
Authorization: Bearer {token}
```

### Clefs (Data Quality Checks)

#### List All Clefs

```http
GET /api/v1/clefs
Authorization: Bearer {token}
```

#### Create a Clef

```http
POST /api/v1/clefs
Authorization: Bearer {token}
Content-Type: application/json

{
  "stave_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Check for NULL emails",
  "type": "null_check",
  "config": {
    "table": "users",
    "column": "email",
    "threshold": 0.01
  },
  "schedule": "0 * * * *",
  "enabled": true
}
```

**Clef Types:**
- `null_check` - Check for NULL values
- `uniqueness_check` - Check for duplicate values
- `range_check` - Check if values are within range
- `pattern_check` - Check against regex pattern
- `custom_sql` - Custom SQL query

#### Get a Clef

```http
GET /api/v1/clefs/{clef_id}
Authorization: Bearer {token}
```

#### Update a Clef

```http
PUT /api/v1/clefs/{clef_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "enabled": false,
  "schedule": "0 */6 * * *"
}
```

#### Delete a Clef

```http
DELETE /api/v1/clefs/{clef_id}
Authorization: Bearer {token}
```

### Check Runs (Execution History)

#### List Check Runs

```http
GET /api/v1/check-runs?clef_id={clef_id}&limit=50
Authorization: Bearer {token}
```

Query Parameters:
- `clef_id` (optional) - Filter by specific clef
- `status` (optional) - Filter by status (success, failed, running)
- `limit` (optional) - Number of results (default: 50)
- `offset` (optional) - Pagination offset

Response:
```json
[
  {
    "id": "run-123",
    "clef_id": "clef-456",
    "status": "success",
    "started_at": "2024-10-03T10:00:00Z",
    "completed_at": "2024-10-03T10:00:05Z",
    "duration_seconds": 5.2,
    "result": {
      "passed": true,
      "anomalies_found": 0,
      "total_records_checked": 10000
    }
  }
]
```

#### Get Check Run Details

```http
GET /api/v1/check-runs/{run_id}
Authorization: Bearer {token}
```

#### Trigger Manual Check Run

```http
POST /api/v1/clefs/{clef_id}/run
Authorization: Bearer {token}
```

### Users

#### Create User

```http
POST /api/v1/users
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "username": "newuser@example.com",
  "email": "newuser@example.com",
  "password": "secure_password",
  "full_name": "New User",
  "role": "viewer"
}
```

**Roles:**
- `admin` - Full access
- `editor` - Can create/edit staves and clefs
- `viewer` - Read-only access

#### List Users

```http
GET /api/v1/users
Authorization: Bearer {admin_token}
```

#### Update User

```http
PUT /api/v1/users/{user_id}
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "role": "editor",
  "is_active": true
}
```

### Health Check

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-10-03T10:00:00Z"
}
```

---

## Python Client Library

For easier interaction with the Podium API:

```python
import httpx
from typing import Dict, List, Any

class DataMetronomeClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.token: str | None = None
    
    async def login(self, username: str, password: str) -> None:
        """Authenticate and store token."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
    
    def _headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        return {"Authorization": f"Bearer {self.token}"}
    
    async def create_stave(self, name: str, type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new stave (data source)."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/staves",
            json={"name": name, "type": type, "config": config},
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def list_staves(self) -> List[Dict[str, Any]]:
        """List all staves."""
        response = await self.client.get(
            f"{self.base_url}/api/v1/staves",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def create_clef(
        self,
        stave_id: str,
        name: str,
        type: str,
        config: Dict[str, Any],
        schedule: str = "0 * * * *",
        enabled: bool = True
    ) -> Dict[str, Any]:
        """Create a new clef (data quality check)."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/clefs",
            json={
                "stave_id": stave_id,
                "name": name,
                "type": type,
                "config": config,
                "schedule": schedule,
                "enabled": enabled
            },
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def list_check_runs(
        self,
        clef_id: str | None = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List check run history."""
        params = {"limit": limit}
        if clef_id:
            params["clef_id"] = clef_id
        
        response = await self.client.get(
            f"{self.base_url}/api/v1/check-runs",
            params=params,
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self) -> None:
        """Close the client."""
        await self.client.aclose()

# Usage
async def main():
    client = DataMetronomeClient()
    
    # Login
    await client.login("user@example.com", "password")
    
    # Create a stave
    stave = await client.create_stave(
        name="Production DB",
        type="postgres",
        config={"host": "db.example.com", "database": "prod"}
    )
    
    # Create a check
    clef = await client.create_clef(
        stave_id=stave["id"],
        name="NULL check",
        type="null_check",
        config={"table": "users", "column": "email"}
    )
    
    # View check runs
    runs = await client.list_check_runs(clef_id=clef["id"])
    print(f"Found {len(runs)} check runs")
    
    await client.close()
```

---

## Error Handling

### HTTP Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
  "detail": "Error message",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-10-03T10:00:00Z"
}
```

### Common Errors

**Authentication Failed:**
```json
{
  "detail": "Incorrect username or password",
  "error_code": "AUTH_FAILED"
}
```

**Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Resource Not Found:**
```json
{
  "detail": "Stave not found",
  "error_code": "NOT_FOUND"
}
```

---

## Rate Limiting

**Coming in Q4 2024**

Rate limits will be applied to prevent abuse:
- 100 requests per minute for authenticated users
- 10 requests per minute for unauthenticated endpoints

---

## Webhooks

**Coming in Q1 2025**

Subscribe to events:
- `check_run.completed` - When a check run finishes
- `anomaly.detected` - When an anomaly is found
- `stave.created` - When a new data source is added

---

## Support

For API questions:
- 📚 Check [Interactive API Docs](http://localhost:8000/docs)
- 🐛 [Report an issue](https://github.com/datametronome/datametronome/issues)
- 💬 [Ask in discussions](https://github.com/datametronome/datametronome/discussions)

---

**Last Updated**: October 2024  
**API Version**: v1

