# Technical Design Document (TDD) - DataMetronome

**Version**: 2.0 (Implementation Blueprint)  
**Date**: August 14, 2025  
**Author**: TheDataMaestros Team  
**Status**: Active

---

## Table of Contents

1. [Overall Project Structure](#1-overall-project-structure-monorepo)
2. [Core Component Specifications](#2-core-component-specifications)
3. [The Stave and Clef: Configuration Deep Dive](#3-the-stave-and-clef-configuration-deep-dive)
4. [Security Architecture](#4-security-architecture)
5. [Data Flow and Orchestration](#5-data-flow-and-orchestration)
6. [API Specifications](#6-api-specifications)
7. [Database Schema](#7-database-schema)
8. [Testing Strategy](#8-testing-strategy)
9. [Deployment Architecture](#9-deployment-architecture)
10. [Performance Optimization](#10-performance-optimization)

---

## 1. Overall Project Structure (Monorepo)

The project is a **monorepo** containing multiple, independent Python packages. This structure promotes code reuse while maintaining clear boundaries between components.

```
datametronome/
├── .gitignore
├── .env.example
├── docker-compose.yml
├── README.md
├── CONTRIBUTING.md
├── LICENSE
│
├── docs/
│   ├── README.md
│   ├── PDD_DataMetronome.md           # This Product Design Doc
│   ├── TDD_DataPulse.md               # This Technical Design Doc
│   ├── architecture.md
│   ├── api.md
│   ├── quickstart.md
│   └── development.md
│
├── datametronome/
│   ├── podium/                        # Headless backend service
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── Dockerfile
│   │   └── datametronome_podium/
│   │       ├── __init__.py
│   │       ├── main.py                # FastAPI app entry point
│   │       ├── core/
│   │       │   ├── config.py          # Settings management
│   │       │   ├── security.py        # JWT, encryption
│   │       │   ├── database.py        # DB connection
│   │       │   └── exceptions.py      # Custom exceptions
│   │       ├── api/
│   │       │   ├── v1/
│   │       │   │   ├── endpoints/
│   │       │   │   │   ├── auth.py    # Login, registration
│   │       │   │   │   ├── staves.py  # Stave CRUD
│   │       │   │   │   ├── checks.py  # Check results
│   │       │   │   │   └── reports.py # Reporting
│   │       │   │   └── deps.py        # Dependencies (auth, etc.)
│   │       │   └── router.py
│   │       ├── services/
│   │       │   ├── stave_service.py   # Stave management
│   │       │   ├── check_service.py   # Check execution
│   │       │   ├── scheduler_service.py # APScheduler
│   │       │   └── reporting_service.py # Report generation
│   │       ├── models/
│   │       │   ├── stave.py           # Pydantic models
│   │       │   ├── check.py
│   │       │   ├── user.py
│   │       │   └── profile.py
│   │       └── plugins/
│   │           └── plugin_loader.py   # Plugin discovery
│   │
│   ├── ui-nuxt/                       # Decoupled UI client
│   │   ├── package.json
│   │   ├── nuxt.config.ts
│   │   ├── app.vue                    # Root layout
│   │   ├── pages/
│   │   │   ├── index.vue              # Dashboard overview
│   │   │   ├── anomalies.vue          # Anomaly insights
│   │   │   ├── staves.vue             # Data source management
│   │   │   └── clefs.vue              # Quality rule configuration
│   │   ├── components/
│   │   │   ├── TrendChart.vue
│   │   │   └── ClefConfigForm.vue
│   │   └── stores/
│   │       └── auth.ts
│   │
│   ├── brain/                         # Analysis libraries
│   │   ├── base/                      # Standard algorithms
│   │   │   ├── pyproject.toml
│   │   │   └── datametronome_brain_base/
│   │   │       ├── __init__.py
│   │   │       ├── forecast.py        # Time series forecasting
│   │   │       ├── drift.py           # Distribution drift
│   │   │       ├── anomaly.py         # Anomaly detection
│   │   │       └── profiling.py       # Statistical profiling
│   │   │
│   │   └── advanced/                  # ML-driven algorithms
│   │       ├── pyproject.toml
│   │       └── datametronome_brain_advanced/
│   │           ├── __init__.py
│   │           ├── deep_learning.py
│   │           └── ensemble.py
│   │
│   └── pulse/                         # DataPulse connectors
│       ├── core/                      # Connector interfaces
│       │   ├── pyproject.toml
│       │   └── metronome_pulse_core/
│       │       ├── __init__.py
│       │       ├── interfaces.py      # Base interfaces
│       │       ├── pool.py            # Connection pooling
│       │       ├── transaction.py     # Transaction mgmt
│       │       └── exceptions.py      # Custom exceptions
│       │
│       ├── postgres/                  # PostgreSQL connector
│       │   ├── pyproject.toml
│       │   └── metronome_pulse_postgres/
│       │       ├── __init__.py
│       │       ├── connector.py       # Main connector
│       │       ├── readonly_connector.py
│       │       ├── writeonly_connector.py
│       │       └── sql_builder.py     # SQL generation
│       │
│       ├── sqlite/                    # SQLite connector
│       │   ├── pyproject.toml
│       │   └── metronome_pulse_sqlite/
│       │       ├── __init__.py
│       │       └── connector.py
│       │
│       └── api/                       # HTTP API connector
│           ├── pyproject.toml
│           └── metronome_pulse_api/
│               ├── __init__.py
│               ├── connector.py
│               └── auth.py            # API authentication
│
└── plugins/                           # Optional integrations
    ├── dbt/
    │   ├── pyproject.toml
    │   └── datametronome_dbt_plugin/
    │       ├── __init__.py
    │       ├── importer.py            # Import dbt tests
    │       └── runner.py              # Run dbt models
    │
    └── great_expectations/
        ├── pyproject.toml
        └── datametronome_gx_plugin/
            ├── __init__.py
            ├── importer.py            # Import GE checkpoints
            └── runner.py              # Run GE validations
```

### Key Design Principles

1. **Monorepo Benefits**:
   - Single source of truth
   - Atomic cross-package changes
   - Shared tooling and CI/CD
   - Easier dependency management

2. **Package Independence**:
   - Each package has its own `pyproject.toml`
   - Independent versioning and releases
   - Can be used standalone
   - Clear dependency graph

3. **Clear Boundaries**:
   - `datametronome-*` packages: Core application components
   - `metronome-pulse-*` packages: Reusable connectors
   - `plugins/`: Optional, installable via entry_points

---

## 2. Core Component Specifications

### 2.1 The Podium (`datametronome-podium`)

#### 2.1.1 Technology Stack
- **Framework**: FastAPI 0.104+
- **Async Runtime**: asyncio
- **Auth**: python-jose[cryptography] for JWT
- **Scheduler**: APScheduler 3.10+
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Encryption**: cryptography (Fernet)
- **Validation**: Pydantic 2.0+

#### 2.1.2 Core Responsibilities

**1. API Server & Authentication**
```python
# datametronome_podium/main.py
from fastapi import FastAPI
from datametronome_podium.api.router import api_router
from datametronome_podium.core.config import settings

app = FastAPI(
    title="DataMetronome Podium API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    await init_db()
    await init_scheduler()
    await load_plugins()

@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown."""
    await shutdown_scheduler()
    await close_db()
```

**2. Configuration & Credential Management**
```python
# datametronome_podium/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Security
    secret_key: str  # Required, min 32 chars
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    
    # Database
    database_url: str = "sqlite:///./datametronome.db"
    
    # Staves
    staves_directory: str = "./staves"
    hot_reload: bool = True
    
    class Config:
        env_prefix = "DATAMETRONOME_"
        env_file = ".env"

settings = Settings()
```

**3. Stateful Metric Collection**
```python
# datametronome_podium/services/check_service.py
async def execute_check_and_profile(stave: Stave) -> CheckResult:
    """Execute check and compute profile metrics."""
    
    # Get data from source
    pulse = get_pulse_connector(stave.source)
    data = await pulse.query(stave.source.query)
    
    # Compute current profile
    current_profile = compute_profile(data)
    
    # Store in profile_history
    await store_profile(
        stave_id=stave.id,
        profile=current_profile,
        timestamp=datetime.utcnow()
    )
    
    # Execute checks
    check_results = []
    for check in stave.clef.checks:
        result = await execute_single_check(check, data, current_profile)
        check_results.append(result)
    
    return CheckResult(
        stave_id=stave.id,
        checks=check_results,
        profile=current_profile
    )
```

**4. Check Orchestration**

The Podium coordinates different check types:

```python
# datametronome_podium/services/check_service.py
async def execute_single_check(
    check: Check, 
    data: list[dict], 
    profile: Profile
) -> CheckResult:
    """Execute a single check based on its type."""
    
    if check.type == "declarative":
        # Level 1: Simple declarative checks
        return await execute_declarative_check(check, data)
    
    elif check.type == "intelligent":
        # Level 2: ML-driven checks using Brain library
        brain = get_brain_algorithm(check.strategy.model)
        return await brain.analyze(data, profile, check.strategy)
    
    elif check.type == "advanced":
        # Level 3: Multi-source checks
        return await execute_advanced_check(check)
    
    elif check.type == "python":
        # Level 4: Custom Python scripts
        return await execute_python_check(check)
    
    else:
        raise ValueError(f"Unknown check type: {check.type}")
```

**5. Scheduler & Job Queue**

```python
# datametronome_podium/services/scheduler_service.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

async def init_scheduler():
    """Initialize scheduler with all staves."""
    staves = await load_all_staves()
    
    for stave in staves:
        if stave.schedule:
            scheduler.add_job(
                func=execute_stave_checks,
                trigger=CronTrigger.from_crontab(stave.schedule),
                args=[stave.id],
                id=f"stave_{stave.id}",
                replace_existing=True
            )
    
    scheduler.start()

async def execute_stave_checks(stave_id: str):
    """Execute all checks for a stave."""
    stave = await get_stave(stave_id)
    result = await execute_check_and_profile(stave)
    await store_check_result(result)
```

**6. Plugin System**

```python
# datametronome_podium/plugins/plugin_loader.py
from importlib.metadata import entry_points

def load_plugins():
    """Discover and load plugins via entry_points."""
    discovered_plugins = entry_points(group='datametronome.plugins')
    
    for plugin in discovered_plugins:
        plugin_class = plugin.load()
        instance = plugin_class()
        register_plugin(instance)
        
        print(f"Loaded plugin: {plugin.name}")
```

Plugin packages declare entry_points in `pyproject.toml`:

```toml
[project.entry-points."datametronome.plugins"]
dbt = "datametronome_dbt_plugin:DbtPlugin"
```

### 2.2 The DataPulse Ecosystem (`metronome-pulse-*`)

#### 2.2.1 Core Principle

**All connectors are independent, `pip` installable, async-first libraries that manage their own connection pools.**

This means:
- ✅ Can be used in any Python project
- ✅ No dependency on DataMetronome
- ✅ Fully async with connection pooling
- ✅ Consistent interface across all connectors
- ✅ Context manager protocol for easy usage

#### 2.2.2 Core Interfaces

```python
# metronome_pulse_core/interfaces.py
from abc import ABC, abstractmethod
from typing import Any

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
        """Check if connection is active."""
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class Readable(ABC):
    """Interface for read operations."""
    
    @abstractmethod
    async def query(
        self,
        query: str,
        params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a query and return results."""
        pass


class Writable(ABC):
    """Interface for write operations."""
    
    @abstractmethod
    async def write(
        self,
        data: list[dict[str, Any]],
        config: dict[str, Any] | None = None
    ) -> int:
        """Write data using the specified configuration."""
        pass
```

#### 2.2.3 PostgreSQL Connector Example

```python
# metronome_pulse_postgres/connector.py
from metronome_pulse_core import Pulse, Readable, Writable
import asyncpg

class PostgresPulse(Pulse, Readable, Writable):
    """High-performance PostgreSQL connector using asyncpg."""
    
    def __init__(
        self,
        host: str,
        port: int = 5432,
        user: str,
        password: str,
        database: str,
        min_pool_size: int = 5,
        max_pool_size: int = 20
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.pool = None
    
    async def connect(self) -> None:
        """Create connection pool."""
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            min_size=self.min_pool_size,
            max_size=self.max_pool_size
        )
    
    async def disconnect(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def is_connected(self) -> bool:
        """Check if pool is active."""
        return self.pool is not None
    
    async def query(
        self,
        query: str,
        params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute query and return results."""
        async with self.pool.acquire() as conn:
            if params:
                rows = await conn.fetch(query, *params.values())
            else:
                rows = await conn.fetch(query)
            
            return [dict(row) for row in rows]
    
    async def write(
        self,
        data: list[dict[str, Any]],
        config: dict[str, Any] | None = None
    ) -> int:
        """Write data based on configuration."""
        config = config or {}
        operation = config.get("operation", "insert")
        table = config["table"]
        
        if operation == "insert":
            return await self._insert(table, data)
        elif operation == "replace":
            return await self._replace(table, data, config)
        elif operation == "copy":
            return await self._copy(table, data, config)
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    async def _insert(self, table: str, data: list[dict]) -> int:
        """Bulk insert using prepared statements."""
        # Implementation details...
        pass
```

#### 2.2.4 Standalone Usage

DataPulse connectors can be used independently:

```python
# In any Python project
from metronome_pulse_postgres import PostgresPulse

async def my_data_pipeline():
    """Use DataPulse in a standalone script."""
    
    async with PostgresPulse(
        host="localhost",
        user="myuser",
        password="mypass",
        database="mydb"
    ) as pulse:
        # Query data
        users = await pulse.query("SELECT * FROM users WHERE active = $1", {"active": True})
        
        # Transform data
        transformed = [transform_user(u) for u in users]
        
        # Write to another table
        await pulse.write(transformed, {
            "operation": "insert",
            "table": "users_transformed"
        })
```

### 2.3 The UI (`ui-nuxt`)

#### 2.3.1 Architecture

The UI is a **pure client** that:
- ✅ Communicates with Podium via REST using a shared typed `apiService`
- ✅ Manages its own authentication state with Pinia + localStorage hydration
- ✅ Ships as a standalone SPA build artifact
- ✅ Can be deployed independently alongside the API

#### 2.3.2 Authentication Flow

```ts
// stores/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { buildApiUrl } from '~/config/app'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => !!token.value && !!user.value)

  async function login(credentials: LoginCredentials) {
    const response = await fetch(buildApiUrl('/auth/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    })

    if (!response.ok) {
      throw new Error('Login failed')
    }

    const data = await response.json()
    token.value = data.access_token
    user.value = { username: credentials.username, email: 'admin@datametronome.dev', name: 'Admin User' }

    if (process.client) {
      localStorage.setItem('auth_token', token.value)
      localStorage.setItem('user_info', JSON.stringify(user.value))
    }

    return { success: true, token: token.value, user: user.value }
  }

  function initializeAuth(): void {
    if (process.client) {
      token.value = localStorage.getItem('auth_token')
      const stored = localStorage.getItem('user_info')
      user.value = stored ? JSON.parse(stored) : null
    }
  }

  initializeAuth()

  return { token, user, isAuthenticated, login, logout, refreshUserData }
})
```

#### 2.3.3 API Communication

```ts
// services/staves.ts
class StavesService {
  private readonly endpoint = '/staves'

  async getAll(): Promise<Stave[]> {
    const response = await apiService.get<Stave[]>(this.endpoint)
    return response.data
  }

  async create(stave: CreateStaveRequest): Promise<Stave> {
    const response = await apiService.post<Stave>(this.endpoint, stave)
    return response.data
  }

  async testConnection(id: string) {
    const response = await apiService.post(`${this.endpoint}/${id}/test-connection`)
    return response.data
  }
}

export const stavesService = new StavesService()
```

### 2.4 The Brain Libraries (`datametronome-brain-*`)

#### 2.4.1 Base Algorithms

```python
# datametronome_brain_base/forecast.py
from statsmodels.tsa.statespace.sarimax import SARIMAX
import pandas as pd

class SarimaForecaster:
    """Time series forecasting using SARIMA."""
    
    def __init__(self, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12)):
        self.order = order
        self.seasonal_order = seasonal_order
        self.model = None
    
    async def train(self, historical_data: list[dict], metric: str):
        """Train SARIMA model on historical data."""
        df = pd.DataFrame(historical_data)
        series = df[metric]
        
        self.model = SARIMAX(
            series,
            order=self.order,
            seasonal_order=self.seasonal_order
        )
        self.model = self.model.fit()
    
    async def forecast(self, steps: int = 1) -> dict:
        """Generate forecast and confidence intervals."""
        forecast = self.model.forecast(steps=steps)
        conf_int = self.model.get_forecast(steps=steps).conf_int()
        
        return {
            "forecast": forecast.tolist(),
            "lower_bound": conf_int.iloc[:, 0].tolist(),
            "upper_bound": conf_int.iloc[:, 1].tolist()
        }
    
    async def detect_anomaly(self, current_value: float, confidence: float = 0.95) -> bool:
        """Check if current value is outside forecast bounds."""
        forecast_result = await self.forecast(steps=1)
        lower = forecast_result["lower_bound"][0]
        upper = forecast_result["upper_bound"][0]
        
        return current_value < lower or current_value > upper
```

#### 2.4.2 Distribution Drift Detection

```python
# datametronome_brain_base/drift.py
from scipy.stats import ks_2samp
import numpy as np

class DriftDetector:
    """Detect distribution drift using statistical tests."""
    
    async def kolmogorov_smirnov_test(
        self,
        baseline_data: list[float],
        current_data: list[float],
        critical_p_value: float = 0.05
    ) -> dict:
        """Perform KS test for distribution drift."""
        statistic, p_value = ks_2samp(baseline_data, current_data)
        
        return {
            "test": "kolmogorov_smirnov",
            "statistic": statistic,
            "p_value": p_value,
            "drift_detected": p_value < critical_p_value,
            "severity": "high" if p_value < 0.01 else "medium" if p_value < critical_p_value else "low"
        }
```

---

## 3. The Stave and Clef: Configuration Deep Dive

### 3.1 Stave Structure

A **Stave** is the atomic unit of monitoring. It contains:
- **Metadata**: name, description, owner
- **Schedule**: when to run (cron expression)
- **Source**: what to monitor (DataPulse connector config)
- **Clef**: how to monitor (checks and rules)

### 3.2 Basic Stave Example

```yaml
# staves/production_users.yaml
staves:
  - name: "production_users_table"
    description: "Monitor production users table for data quality"
    schedule: "*/15 * * * *"  # Every 15 minutes
    
    source:
      type: metronome-pulse-postgres
      credentials:
        host: "{{ env.PROD_DB_HOST }}"
        port: 5432
        user: "{{ env.PROD_DB_USER }}"
        password: "{{ env.PROD_DB_PASSWORD }}"
        database: "production"
      query: "SELECT * FROM users WHERE updated_at >= NOW() - INTERVAL '1 hour'"
    
    clef:
      owner: "@data-platform-team"
      tags: ["production", "users", "critical"]
      
      checks:
        - name: "minimum_row_count"
          check: row_count
          fail: "< 1000"
          warn: "< 5000"
        
        - name: "data_freshness"
          check: freshness
          column: "updated_at"
          fail: "> 24 hours"
          warn: "> 12 hours"
        
        - name: "email_not_null"
          check: null_check
          column: "email"
          fail: "> 0"
```

### 3.3 The Tiered Check System

DataMetronome provides **four levels** of check complexity, allowing teams to use the right tool for each use case.

#### **Level 1: Declarative Checks (UI-Friendly)**

**Philosophy**: Simple, declarative validation that can be created via UI or YAML without any programming knowledge.

**Use Case**: Analysts, non-technical users setting up basic validation.

```yaml
checks:
  # Row count validation
  - check: row_count
    fail: "< 1000"
    warn: "< 5000"
  
  # Freshness check
  - check: freshness
    column: "updated_at"
    fail: "> 24 hours"
    warn: "> 12 hours"
  
  # Null value detection
  - check: null_check
    column: "email"
    fail: "> 0"  # Fail if any nulls
  
  # Uniqueness validation
  - check: unique_check
    column: "user_id"
    fail: "< 100%"
  
  # Range validation
  - check: range_check
    column: "age"
    min: 0
    max: 120
    fail: "> 1%"  # Fail if >1% out of range
  
  # Value set validation
  - check: value_set_check
    column: "status"
    allowed_values: ["active", "inactive", "suspended"]
    fail: "> 0"  # Fail if any invalid values
```

**Implementation**:
```python
# datametronome_podium/services/check_service.py
async def execute_declarative_check(check: Check, data: list[dict]) -> CheckResult:
    """Execute Level 1 declarative check."""
    
    if check.check == "row_count":
        count = len(data)
        threshold = parse_threshold(check.fail)
        passed = evaluate_threshold(count, threshold)
        
        return CheckResult(
            check_name=check.name,
            passed=passed,
            actual_value=count,
            expected=check.fail,
            message=f"Row count: {count}"
        )
    
    elif check.check == "freshness":
        latest = max(row[check.column] for row in data)
        age = datetime.utcnow() - latest
        threshold = parse_duration(check.fail)
        passed = age <= threshold
        
        return CheckResult(
            check_name=check.name,
            passed=passed,
            actual_value=str(age),
            expected=check.fail,
            message=f"Data age: {age}"
        )
    
    # ... other check types
```

#### **Level 2: Intelligent Checks (ML-Driven)**

**Philosophy**: Proactive anomaly detection using historical data and ML algorithms. No manual threshold setting required.

**Use Case**: Detecting unknown anomalies, data drift, and subtle changes.

```yaml
checks:
  # Time series forecasting
  - check: forecast
    metric: "row_count"
    strategy:
      model: "sarima"
      confidence: 99  # 99% confidence interval
      training_period_days: 90
      seasonality: "weekly"
  
  # Distribution drift detection
  - check: data_profile_drift
    column: "age"
    strategy:
      test: "kolmogorov_smirnov"
      critical_p_value: 0.05
      baseline_period_days: 30
  
  # Multi-variate anomaly detection
  - check: anomaly_detection
    columns: ["age", "income", "transaction_amount"]
    strategy:
      algorithm: "isolation_forest"
      contamination: 0.01
      n_estimators: 100
  
  # Trend detection
  - check: trend_analysis
    metric: "avg_transaction_amount"
    strategy:
      method: "mann_kendall"
      significance_level: 0.05
```

**Implementation**:
```python
# datametronome_podium/services/check_service.py
async def execute_intelligent_check(check: Check, data: list[dict], profile: Profile) -> CheckResult:
    """Execute Level 2 ML-driven check."""
    
    if check.check == "forecast":
        # Get historical profile data
        historical = await get_profile_history(
            stave_id=check.stave_id,
            metric=check.metric,
            days=check.strategy.training_period_days
        )
        
        # Train forecaster
        forecaster = SarimaForecaster(
            seasonal_order=get_seasonal_order(check.strategy.seasonality)
        )
        await forecaster.train(historical, check.metric)
        
        # Check current value against forecast
        current_value = profile[check.metric]
        is_anomaly = await forecaster.detect_anomaly(
            current_value,
            confidence=check.strategy.confidence / 100
        )
        
        return CheckResult(
            check_name=check.name,
            passed=not is_anomaly,
            actual_value=current_value,
            expected="Within forecast bounds",
            metadata={
                "forecast": await forecaster.forecast(),
                "model": "SARIMA",
                "training_samples": len(historical)
            }
        )
    
    elif check.check == "data_profile_drift":
        # Get baseline distribution
        baseline = await get_baseline_distribution(
            stave_id=check.stave_id,
            column=check.column,
            days=check.strategy.baseline_period_days
        )
        
        # Get current distribution
        current = [row[check.column] for row in data]
        
        # Perform KS test
        drift_detector = DriftDetector()
        result = await drift_detector.kolmogorov_smirnov_test(
            baseline,
            current,
            check.strategy.critical_p_value
        )
        
        return CheckResult(
            check_name=check.name,
            passed=not result["drift_detected"],
            actual_value=f"p-value: {result['p_value']:.4f}",
            expected=f"p-value >= {check.strategy.critical_p_value}",
            metadata=result
        )
```

#### **Level 3: Advanced Declarative Checks (For Analysts)**

**Philosophy**: Complex, multi-source logic without writing Python code. Declarative YAML for sophisticated validation.

**Use Case**: Cross-system reconciliation, lookup validation, referential integrity across sources.

**Example 1: Reconciliation**
```yaml
checks:
  - check: reconcile
    description: "Ensure all users in DB also exist in CRM API"
    
    source_a:
      type: metronome-pulse-postgres
      credentials:
        host: "{{ env.DB_HOST }}"
        database: "production"
      query: "SELECT user_id FROM public.users"
    
    source_b:
      type: metronome-pulse-api
      credentials:
        base_url: "https://crm.example.com"
        api_key: "{{ env.CRM_API_KEY }}"
      query:
        endpoint: "/users"
        method: "GET"
    
    strategy:
      join_on: ["user_id"]
      type: "full_match"  # Both sides must match exactly
      tolerance: 0  # Allow 0 mismatches
```

**Example 2: Lookup Validation**
```yaml
checks:
  - check: lookup_validation
    description: "Ensure all campaign IDs in analytics exist in active campaigns"
    
    lookup:
      pulse:
        type: metronome-pulse-api
        credentials:
          base_url: "https://api.example.com"
          api_key: "{{ env.API_KEY }}"
      query:
        endpoint: "/campaigns"
        params:
          status: "active"
      key_column: "id"
    
    validation:
      pulse:
        type: metronome-pulse-postgres
        credentials:
          host: "{{ env.ANALYTICS_DB_HOST }}"
          database: "analytics"
      query: |
        SELECT DISTINCT campaign_id 
        FROM analytics.traffic 
        WHERE date >= CURRENT_DATE - INTERVAL '7 days'
      key_column: "campaign_id"
    
    enforce: "existence_for_all"  # All validation keys must exist in lookup
```

**Example 3: Referential Integrity**
```yaml
checks:
  - check: referential_integrity
    description: "Ensure all order.user_id values exist in users table"
    
    parent:
      pulse:
        type: metronome-pulse-postgres
        credentials: "{{ env.DB_CREDS }}"
      table: "users"
      key_column: "user_id"
    
    child:
      pulse:
        type: metronome-pulse-postgres
        credentials: "{{ env.DB_CREDS }}"
      table: "orders"
      key_column: "user_id"
    
    fail: "> 0"  # Fail if any orphaned records
```

**Implementation**:
```python
# datametronome_podium/services/check_service.py
async def execute_advanced_check(check: Check) -> CheckResult:
    """Execute Level 3 advanced declarative check."""
    
    if check.check == "reconcile":
        # Get data from source A
        pulse_a = get_pulse_connector(check.source_a.type)
        await pulse_a.connect()
        data_a = await pulse_a.query(check.source_a.query)
        
        # Get data from source B
        pulse_b = get_pulse_connector(check.source_b.type)
        await pulse_b.connect()
        data_b = await pulse_b.query(check.source_b.query)
        
        # Perform reconciliation
        join_keys = check.strategy.join_on
        set_a = {tuple(row[k] for k in join_keys) for row in data_a}
        set_b = {tuple(row[k] for k in join_keys) for row in data_b}
        
        only_in_a = set_a - set_b
        only_in_b = set_b - set_a
        
        if check.strategy.type == "full_match":
            passed = len(only_in_a) == 0 and len(only_in_b) == 0
        
        return CheckResult(
            check_name=check.name,
            passed=passed,
            actual_value=f"{len(only_in_a)} in A only, {len(only_in_b)} in B only",
            expected="Full match",
            metadata={
                "source_a_count": len(data_a),
                "source_b_count": len(data_b),
                "only_in_a": list(only_in_a)[:10],  # Sample
                "only_in_b": list(only_in_b)[:10]   # Sample
            }
        )
    
    elif check.check == "lookup_validation":
        # Get lookup data (valid keys)
        lookup_pulse = get_pulse_connector(check.lookup.pulse.type)
        await lookup_pulse.connect()
        lookup_data = await lookup_pulse.query(check.lookup.query)
        valid_keys = {row[check.lookup.key_column] for row in lookup_data}
        
        # Get validation data (keys to validate)
        validation_pulse = get_pulse_connector(check.validation.pulse.type)
        await validation_pulse.connect()
        validation_data = await validation_pulse.query(check.validation.query)
        keys_to_validate = {row[check.validation.key_column] for row in validation_data}
        
        # Check for invalid keys
        invalid_keys = keys_to_validate - valid_keys
        
        passed = len(invalid_keys) == 0
        
        return CheckResult(
            check_name=check.name,
            passed=passed,
            actual_value=f"{len(invalid_keys)} invalid keys",
            expected="All keys valid",
            metadata={
                "valid_keys_count": len(valid_keys),
                "validated_keys_count": len(keys_to_validate),
                "invalid_keys": list(invalid_keys)[:10]  # Sample
            }
        )
```

#### **Level 4: Custom Code (Developer Escape Hatch)**

**Philosophy**: Ultimate flexibility for business logic that cannot be declared in YAML. Clean separation between configuration (YAML) and code (Python scripts).

**Use Case**: Complex business rules, multi-step validation, integration with external systems.

```yaml
checks:
  - check: python
    description: "Validate campaign traffic matches marketing spend"
    
    # YAML only REFERENCES the code
    script_path: "datametronome_scripts/check_campaign_traffic.py"
    
    # Parameters passed to the script
    params:
      tag: "premium"
      min_roi: 2.0
      lookback_days: 7
```

**Python Script**:
```python
# datametronome_scripts/check_campaign_traffic.py
from metronome_pulse_postgres import PostgresPulse
from metronome_pulse_api import APIPulse

async def check(params: dict, context: dict) -> dict:
    """
    Custom check: Validate campaign traffic matches marketing spend.
    
    Args:
        params: Parameters from YAML (tag, min_roi, lookback_days)
        context: DataMetronome context (connectors, credentials, etc.)
    
    Returns:
        CheckResult dict with passed, actual_value, expected, message
    """
    
    # Get connectors from context
    db_pulse = context.get_connector("analytics_db")
    api_pulse = context.get_connector("marketing_api")
    
    # Query traffic data
    traffic_query = f"""
        SELECT campaign_id, SUM(conversions) as total_conversions
        FROM analytics.traffic
        WHERE date >= CURRENT_DATE - INTERVAL '{params['lookback_days']} days'
          AND campaign_tag = %s
        GROUP BY campaign_id
    """
    traffic_data = await db_pulse.query(traffic_query, {"tag": params["tag"]})
    
    # Query marketing spend
    spend_data = await api_pulse.query({
        "endpoint": "/campaigns/spend",
        "params": {
            "tag": params["tag"],
            "days": params["lookback_days"]
        }
    })
    
    # Calculate ROI for each campaign
    failed_campaigns = []
    for traffic in traffic_data:
        campaign_id = traffic["campaign_id"]
        spend = next(
            (s["amount"] for s in spend_data if s["campaign_id"] == campaign_id),
            0
        )
        
        if spend > 0:
            roi = traffic["total_conversions"] / spend
            if roi < params["min_roi"]:
                failed_campaigns.append({
                    "campaign_id": campaign_id,
                    "roi": roi,
                    "conversions": traffic["total_conversions"],
                    "spend": spend
                })
    
    # Return result
    passed = len(failed_campaigns) == 0
    
    return {
        "passed": passed,
        "actual_value": f"{len(failed_campaigns)} campaigns below ROI threshold",
        "expected": f"All campaigns with ROI >= {params['min_roi']}",
        "message": f"Checked {len(traffic_data)} campaigns",
        "metadata": {
            "failed_campaigns": failed_campaigns,
            "total_campaigns": len(traffic_data),
            "min_roi": params["min_roi"]
        }
    }
```

**Implementation**:
```python
# datametronome_podium/services/check_service.py
async def execute_python_check(check: Check) -> CheckResult:
    """Execute Level 4 custom Python check."""
    
    # Load the Python script
    script_path = Path(check.script_path)
    spec = importlib.util.spec_from_file_location("custom_check", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Prepare context
    context = CheckContext(
        connectors=get_available_connectors(),
        credentials=get_credentials_for_stave(check.stave_id),
        profile=get_latest_profile(check.stave_id)
    )
    
    # Execute the check function
    result = await module.check(check.params, context)
    
    return CheckResult(
        check_name=check.name,
        passed=result["passed"],
        actual_value=result["actual_value"],
        expected=result["expected"],
        message=result["message"],
        metadata=result.get("metadata", {})
    )
```

### 3.4 Environment Variable Interpolation

Stave configurations support environment variable interpolation for security:

```yaml
source:
  type: metronome-pulse-postgres
  credentials:
    host: "{{ env.PROD_DB_HOST }}"
    port: "{{ env.PROD_DB_PORT }}"
    user: "{{ env.PROD_DB_USER }}"
    password: "{{ env.PROD_DB_PASSWORD }}"
    database: "{{ env.PROD_DB_NAME }}"
```

**Implementation**:
```python
# datametronome_podium/core/config.py
import re
import os

def interpolate_env_vars(config: dict) -> dict:
    """Recursively interpolate environment variables in config."""
    
    if isinstance(config, dict):
        return {k: interpolate_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [interpolate_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Match {{ env.VAR_NAME }}
        pattern = r'\{\{\s*env\.(\w+)\s*\}\}'
        
        def replacer(match):
            var_name = match.group(1)
            value = os.getenv(var_name)
            if value is None:
                raise ValueError(f"Environment variable not found: {var_name}")
            return value
        
        return re.sub(pattern, replacer, config)
    else:
        return config
```

---

## 4. Security Architecture

### 4.1 Authentication (JWT)

```python
# datametronome_podium/core/security.py
from jose import JWTError, jwt
from datetime import datetime, timedelta
from datametronome_podium.core.config import settings

def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        raise AuthenticationError("Invalid token")
```

### 4.2 Secrets Management

DataMetronome uses a **layered approach** for managing secrets:

**1. Environment Variables (Recommended)**
```bash
# .env file (local development)
DATAMETRONOME_SECRET_KEY="your-super-secret-key-at-least-32-chars"
PROD_DB_HOST="prod-db.example.com"
PROD_DB_USER="readonly_user"
PROD_DB_PASSWORD="secure_password"
```

**2. Docker Secrets**
```yaml
# docker-compose.yml
services:
  podium:
    env_file:
      - .env
      - .env.production  # Production secrets
    secrets:
      - db_password

secrets:
  db_password:
    external: true
```

**3. Production Secrets Management**
- **Kubernetes**: Use Kubernetes Secrets or external secrets operators
- **AWS**: AWS Secrets Manager
- **GCP**: Google Secret Manager
- **Azure**: Azure Key Vault
- **HashiCorp Vault**: Enterprise-grade secrets management

### 4.3 At-Rest Encryption

For credentials stored dynamically via the API (not in YAML), the Podium uses **Fernet symmetric encryption**:

```python
# datametronome_podium/core/security.py
from cryptography.fernet import Fernet
from datametronome_podium.core.config import settings

def get_fernet() -> Fernet:
    """Get Fernet cipher using the master secret key."""
    # Derive a Fernet key from the secret_key
    key = settings.secret_key.encode()[:32]  # Fernet needs 32 bytes
    key = base64.urlsafe_b64encode(key.ljust(32, b'0'))
    return Fernet(key)

def encrypt_credentials(credentials: dict) -> str:
    """Encrypt credentials for storage."""
    fernet = get_fernet()
    json_str = json.dumps(credentials)
    encrypted = fernet.encrypt(json_str.encode())
    return encrypted.decode()

def decrypt_credentials(encrypted: str) -> dict:
    """Decrypt credentials from storage."""
    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted.encode())
    return json.loads(decrypted.decode())
```

**Usage**:
```python
# When storing credentials via API
@router.post("/staves")
async def create_stave(stave: StaveCreate):
    # Encrypt sensitive credentials
    if stave.source.credentials:
        encrypted_creds = encrypt_credentials(stave.source.credentials)
        stave.source.credentials = encrypted_creds
    
    # Store in database
    await store_stave(stave)

# When loading credentials for execution
async def execute_stave(stave_id: str):
    stave = await get_stave(stave_id)
    
    # Decrypt credentials
    if stave.source.credentials:
        decrypted_creds = decrypt_credentials(stave.source.credentials)
        stave.source.credentials = decrypted_creds
    
    # Use decrypted credentials
    pulse = get_pulse_connector(stave.source.type, **decrypted_creds)
```

### 4.4 Authorization (RBAC)

Future implementation will include role-based access control:

```python
# datametronome_podium/models/user.py
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class User(BaseModel):
    id: str
    username: str
    email: str
    role: Role
    permissions: list[str] = []
```

---

## 5. Data Flow and Orchestration

### 5.1 Scheduled Check Execution Flow

```mermaid
sequenceDiagram
    participant Scheduler
    participant CheckService
    participant Pulse
    participant Brain
    participant DB
    
    Scheduler->>CheckService: execute_stave_checks(stave_id)
    CheckService->>DB: load_stave(stave_id)
    DB-->>CheckService: stave_config
    
    CheckService->>Pulse: connect()
    CheckService->>Pulse: query(stave.source.query)
    Pulse-->>CheckService: raw_data
    
    CheckService->>CheckService: compute_profile(raw_data)
    CheckService->>DB: store_profile(profile)
    
    loop For each check in stave.clef.checks
        alt Level 1: Declarative
            CheckService->>CheckService: execute_declarative_check()
        else Level 2: ML
            CheckService->>Brain: analyze(data, profile, strategy)
            Brain-->>CheckService: ml_result
        else Level 3: Advanced
            CheckService->>Pulse: multi_source_query()
            Pulse-->>CheckService: reconciliation_result
        else Level 4: Custom
            CheckService->>CheckService: execute_python_script()
        end
        
        CheckService->>DB: store_check_result(result)
    end
    
    CheckService->>Pulse: disconnect()
    CheckService-->>Scheduler: execution_complete
```

### 5.2 On-Demand Check Execution (API Request)

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Queue
    participant CheckService
    participant DB
    
    Client->>API: POST /api/v1/staves/{id}/run
    API->>API: verify_jwt_token()
    API->>Queue: enqueue_job(stave_id)
    API-->>Client: job_id (202 Accepted)
    
    Queue->>CheckService: process_job(job_id)
    CheckService->>CheckService: execute_stave_checks(stave_id)
    CheckService->>DB: store_results()
    CheckService->>Queue: mark_job_complete(job_id)
    
    Client->>API: GET /api/v1/jobs/{job_id}
    API->>DB: get_job_status(job_id)
    DB-->>API: status, results
    API-->>Client: job_status_response
```

### 5.3 Hot Reload of Stave Configuration

```python
# datametronome_podium/services/stave_service.py
import asyncio
from watchfiles import awatch

async def watch_staves_directory():
    """Watch staves directory for changes and hot-reload."""
    
    async for changes in awatch(settings.staves_directory):
        for change_type, file_path in changes:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                if change_type == "added" or change_type == "modified":
                    await reload_stave(file_path)
                elif change_type == "deleted":
                    await remove_stave(file_path)

async def reload_stave(file_path: str):
    """Reload a stave from file and update scheduler."""
    stave = await load_stave_from_yaml(file_path)
    
    # Validate stave
    await validate_stave(stave)
    
    # Update in database
    await upsert_stave(stave)
    
    # Update scheduler
    if stave.schedule:
        scheduler.reschedule_job(
            job_id=f"stave_{stave.id}",
            trigger=CronTrigger.from_crontab(stave.schedule)
        )
    
    print(f"Reloaded stave: {stave.name}")
```

---

## 6. API Specifications

### 6.1 API Endpoints

#### Authentication
```
POST   /api/v1/auth/register    # Register new user
POST   /api/v1/auth/login       # Login and get JWT token
POST   /api/v1/auth/refresh     # Refresh access token
GET    /api/v1/auth/me          # Get current user info
```

#### Staves
```
GET    /api/v1/staves           # List all staves
POST   /api/v1/staves           # Create new stave
GET    /api/v1/staves/{id}      # Get stave by ID
PUT    /api/v1/staves/{id}      # Update stave
DELETE /api/v1/staves/{id}      # Delete stave
POST   /api/v1/staves/{id}/run  # Run stave checks on-demand
```

#### Check Results
```
GET    /api/v1/check-results                    # List check results (with filters)
GET    /api/v1/check-results/{id}               # Get single check result
GET    /api/v1/staves/{id}/check-results        # Get check results for a stave
GET    /api/v1/staves/{id}/check-results/latest # Get latest check results
```

#### Profile History
```
GET    /api/v1/staves/{id}/profile-history      # Get profile history for a stave
GET    /api/v1/staves/{id}/profile-history/latest # Get latest profile
```

#### Reports
```
GET    /api/v1/reports/system-health            # Get system health metrics
GET    /api/v1/reports/stave-summary            # Get summary for all staves
GET    /api/v1/reports/anomalies                # Get recent anomalies
```

### 6.2 API Request/Response Examples

#### Create Stave
```http
POST /api/v1/staves
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "production_users",
  "description": "Monitor production users table",
  "schedule": "*/15 * * * *",
  "source": {
    "type": "metronome-pulse-postgres",
    "credentials": {
      "host": "prod-db.example.com",
      "port": 5432,
      "user": "readonly",
      "password": "encrypted_password",
      "database": "production"
    },
    "query": "SELECT * FROM users"
  },
  "clef": {
    "owner": "@data-team",
    "checks": [
      {
        "name": "row_count",
        "check": "row_count",
        "fail": "< 1000"
      }
    ]
  }
}
```

Response:
```json
{
  "id": "stave_01h8x9y2z3",
  "name": "production_users",
  "description": "Monitor production users table",
  "schedule": "*/15 * * * *",
  "created_at": "2025-08-14T10:00:00Z",
  "updated_at": "2025-08-14T10:00:00Z",
  "status": "active"
}
```

#### Run Stave On-Demand
```http
POST /api/v1/staves/stave_01h8x9y2z3/run
Authorization: Bearer <jwt_token>
```

Response:
```json
{
  "job_id": "job_abc123",
  "status": "queued",
  "message": "Check execution queued",
  "status_url": "/api/v1/jobs/job_abc123"
}
```

#### Get Latest Check Results
```http
GET /api/v1/staves/stave_01h8x9y2z3/check-results/latest
Authorization: Bearer <jwt_token>
```

Response:
```json
{
  "stave_id": "stave_01h8x9y2z3",
  "stave_name": "production_users",
  "executed_at": "2025-08-14T10:15:00Z",
  "overall_passed": true,
  "checks": [
    {
      "name": "row_count",
      "passed": true,
      "actual_value": 15000,
      "expected": ">= 1000",
      "message": "Row count within expected range"
    }
  ],
  "profile": {
    "row_count": 15000,
    "column_count": 12,
    "null_counts": {...},
    "distributions": {...}
  }
}
```

---

## 7. Database Schema

### 7.1 Tables

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### staves
```sql
CREATE TABLE staves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    schedule VARCHAR(255),  -- Cron expression
    source_config JSONB NOT NULL,  -- Encrypted source configuration
    clef_config JSONB NOT NULL,    -- Check configuration
    status VARCHAR(50) DEFAULT 'active',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### check_runs
```sql
CREATE TABLE check_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stave_id UUID REFERENCES staves(id) ON DELETE CASCADE,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    overall_passed BOOLEAN NOT NULL,
    check_results JSONB NOT NULL,  -- Array of check results
    error TEXT
);

CREATE INDEX idx_check_runs_stave_id ON check_runs(stave_id);
CREATE INDEX idx_check_runs_executed_at ON check_runs(executed_at);
```

#### profile_history
```sql
CREATE TABLE profile_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stave_id UUID REFERENCES staves(id) ON DELETE CASCADE,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    profile_data JSONB NOT NULL,  -- Statistical profile
    UNIQUE(stave_id, recorded_at)
);

CREATE INDEX idx_profile_history_stave_id ON profile_history(stave_id);
CREATE INDEX idx_profile_history_recorded_at ON profile_history(recorded_at);
```

#### jobs
```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(50) NOT NULL,  -- 'check_run', 'forecast_train', etc.
    stave_id UUID REFERENCES staves(id),
    status VARCHAR(50) NOT NULL,  -- 'queued', 'running', 'completed', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    result JSONB
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
```

---

## 8. Testing Strategy

### 8.1 Unit Tests
- Test individual functions and classes in isolation
- Mock external dependencies (database, APIs, connectors)
- High coverage (>80%) for core logic

```python
# tests/unit/test_check_service.py
import pytest
from unittest.mock import AsyncMock
from datametronome_podium.services.check_service import execute_declarative_check

@pytest.mark.asyncio
async def test_row_count_check_passes():
    """Test that row_count check passes when threshold is met."""
    check = Check(check="row_count", fail="< 1000")
    data = [{"id": i} for i in range(1500)]
    
    result = await execute_declarative_check(check, data)
    
    assert result.passed == True
    assert result.actual_value == 1500
```

### 8.2 Integration Tests
- Test interactions between components
- Use real database (Docker container for tests)
- Test DataPulse connectors against real databases

```python
# tests/integration/test_postgres_pulse.py
import pytest
from metronome_pulse_postgres import PostgresPulse

@pytest.mark.asyncio
async def test_postgres_pulse_query(postgres_container):
    """Test PostgresPulse can query real database."""
    pulse = PostgresPulse(
        host=postgres_container.host,
        port=postgres_container.port,
        user="test",
        password="test",
        database="test"
    )
    
    await pulse.connect()
    
    # Insert test data
    await pulse.write([
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ], {"operation": "insert", "table": "users"})
    
    # Query data
    results = await pulse.query("SELECT * FROM users ORDER BY id")
    
    assert len(results) == 2
    assert results[0]["name"] == "Alice"
    
    await pulse.disconnect()
```

### 8.3 End-to-End Tests
- Test complete workflows from API to database
- Use Docker Compose to spin up full stack
- Test UI interactions with Selenium/Playwright

```python
# tests/e2e/test_stave_execution.py
import pytest
import httpx

@pytest.mark.asyncio
async def test_create_and_run_stave(podium_api, postgres_container):
    """Test creating a stave and running it end-to-end."""
    # Login
    login_response = httpx.post(
        f"{podium_api}/api/v1/auth/login",
        json={"username": "test", "password": "test"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create stave
    stave_config = {
        "name": "test_stave",
        "source": {...},
        "clef": {
            "checks": [{"check": "row_count", "fail": "< 1"}]
        }
    }
    create_response = httpx.post(
        f"{podium_api}/api/v1/staves",
        headers=headers,
        json=stave_config
    )
    stave_id = create_response.json()["id"]
    
    # Run stave
    run_response = httpx.post(
        f"{podium_api}/api/v1/staves/{stave_id}/run",
        headers=headers
    )
    job_id = run_response.json()["job_id"]
    
    # Wait for completion and get results
    # ... (polling logic)
    
    # Assert results
    assert results["overall_passed"] == True
```

### 8.4 Performance Tests
- Benchmark DataPulse connector performance
- Load test Podium API
- Profile check execution times

```python
# tests/performance/test_postgres_performance.py
import pytest
import time
from metronome_pulse_postgres import PostgresPulse

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_bulk_insert_performance(postgres_container):
    """Benchmark bulk insert performance."""
    pulse = PostgresPulse(...)
    await pulse.connect()
    
    data = [{"id": i, "value": f"value_{i}"} for i in range(100000)]
    
    start = time.time()
    await pulse.write(data, {"operation": "copy", "table": "benchmark"})
    duration = time.time() - start
    
    throughput = len(data) / duration
    print(f"Throughput: {throughput:.0f} rows/sec")
    
    assert throughput > 10000  # At least 10K rows/sec
```

---

## 9. Deployment Architecture

### 9.1 Docker Compose (Development)

```yaml
# docker-compose.yml
version: '3.8'

services:
  podium:
    build:
      context: .
      dockerfile: datametronome/podium/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATAMETRONOME_SECRET_KEY=${SECRET_KEY}
      - DATAMETRONOME_DATABASE_URL=postgresql://user:pass@postgres:5432/datametronome
    volumes:
      - ./staves:/app/staves
      - ./datametronome_scripts:/app/datametronome_scripts
    depends_on:
      - postgres
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=datametronome
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### 9.2 Kubernetes (Production)

```yaml
# k8s/podium-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: datametronome-podium
spec:
  replicas: 3
  selector:
    matchLabels:
      app: podium
  template:
    metadata:
      labels:
        app: podium
    spec:
      containers:
      - name: podium
        image: datametronome/podium:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATAMETRONOME_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: datametronome-secrets
              key: secret-key
        - name: DATAMETRONOME_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: datametronome-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

---

## 10. Performance Optimization

### 10.1 Connection Pooling

All DataPulse connectors use connection pooling:
- **Minimum Pool Size**: 5 connections
- **Maximum Pool Size**: 20 connections
- **Connection Timeout**: 30 seconds
- **Idle Timeout**: 300 seconds (5 minutes)

### 10.2 Async Everywhere

- All I/O operations are async
- No blocking operations in hot paths
- Concurrent check execution where possible

### 10.3 Caching

```python
# Cache profile history for ML checks
from functools import lru_cache

@lru_cache(maxsize=1000)
async def get_profile_history_cached(stave_id: str, days: int) -> list[dict]:
    """Get profile history with caching."""
    return await get_profile_history(stave_id, days)
```

### 10.4 Batch Operations

- Batch multiple checks into single database query when possible
- Use COPY protocol for bulk inserts (PostgreSQL)
- Batch API calls to external services

---

## Appendices

### A. Glossary

- **Stave**: Atomic unit of monitoring configuration
- **Clef**: Set of checks to be performed
- **Podium**: Headless backend service
- **DataPulse**: High-performance connector library
- **Brain**: ML analysis library
- **Check**: Single validation or analysis
- **Profile**: Statistical summary of dataset
- **Job**: Asynchronous background task

### B. References

- FastAPI: https://fastapi.tiangolo.com/
- asyncpg: https://magicstack.github.io/asyncpg/
- APScheduler: https://apscheduler.readthedocs.io/
- Pydantic: https://docs.pydantic.dev/
- Cryptography: https://cryptography.io/

### C. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-03-21 | Initial TDD |
| 2.0 | 2025-08-14 | Implementation Blueprint - added Stave deep dive, tiered checks, security, data flow |

---

**Document Status**: ✅ Active  
**Last Updated**: August 14, 2025  
**Maintained By**: TheDataMaestros Team  
**Next Review**: November 14, 2025

---

*"DataMetronome: Architected for Excellence"* 🎵
