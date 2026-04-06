# 🎵 DataMetronome

<div align="center">
  <img src="ui-nuxt/public/favicon.svg" alt="DataMetronome Logo" width="160">

  **Open-Source Data Quality Monitoring with AI-Powered Multi-Agent Assistance**

  [![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
  [![Nuxt 3](https://img.shields.io/badge/Nuxt-3-00DC82.svg)](https://nuxt.com/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)
  [![Pydantic AI](https://img.shields.io/badge/Pydantic_AI-agents-e92063.svg)](https://ai.pydantic.dev/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/TheDataMaestros/datametronome)
</div>

---

## 🚀 What is DataMetronome?

DataMetronome is an open-source data quality monitoring platform that combines declarative YAML-based checks with ML-powered anomaly detection and an AI multi-agent assistant. Define quality rules as code, get SARIMA forecasting and drift detection out of the box, and chat with an AI that can investigate failures, generate reports, and configure new checks — all from a single dashboard.

---

## 🏗️ Architecture Overview

```mermaid
graph TB
    subgraph "Frontend"
        UI[Nuxt 3 Dashboard]
        Chat[AI Chat Widget]
    end

    subgraph "API Layer"
        API[FastAPI]
        Auth[JWT Auth]
    end

    subgraph "AI Orchestration"
        Router[Router Agent<br/>Intent Classification]
        Config[Config Agent]
        Investigation[Investigation Agent]
        Report[Report Agent]
    end

    subgraph "Processing"
        Scheduler[APScheduler]
        Executor[Check Executor]
        Brain[Brain Library<br/>SARIMA / KS Drift / Isolation Forest]
    end

    subgraph "Data Layer"
        QE[QueryExecutor]
        Adapter[QueryAdapter]
        PG[PostgreSQL]
        SQLite[SQLite]
    end

    UI --> API
    Chat --> API
    API --> Router
    Router --> Config
    Router --> Investigation
    Router --> Report
    API --> Scheduler
    Scheduler --> Executor
    Executor --> Brain
    Config --> QE
    Investigation --> QE
    Report --> QE
    Executor --> QE
    QE --> Adapter
    Adapter --> PG
    Adapter --> SQLite
```

---

## ✨ Key Features

### 🎯 Data Quality Monitoring
Define checks as code in YAML and run them on a schedule across multiple databases:
- **row_count** — Ensure minimum/maximum record volumes
- **freshness** — Detect stale data and pipeline delays
- **null_percentage** — Track data completeness
- **value_range** — Enforce business-rule bounds
- **pattern_match** — Validate formats with regex
- **unique_percentage** — Catch duplicates

### 🧠 ML-Powered Anomaly Detection
Advanced statistical checks that learn from your data:
- **SARIMA Forecasting** — Predict expected metrics and flag deviations
- **KS Drift Detection** — Spot when data distributions shift
- **Isolation Forest** — Identify outliers in multi-dimensional data

### 🤖 AI Multi-Agent Assistant
Chat with an AI that understands your data quality pipeline:
- **Structured LLM routing** via Pydantic AI with intent classification
- **3 specialized agents** — Config, Investigation, Report
- **Dispatch modes** — Single, chain, or parallel agent execution
- **Multi-provider** — Anthropic, OpenAI, Gemini, Ollama
- **Conversation memory** and workflow checkpoints

---

## 💬 Multi-Agent Chat Flow

```mermaid
sequenceDiagram
    participant U as User
    participant R as Router Agent
    participant O as Orchestrator
    participant A as Sub-Agent
    participant T as Agent Tools
    participant DB as Database

    U->>R: "Why are my checks failing?"
    R->>R: Classify intent (investigation)
    R->>O: RoutingDecision(intent=investigation, mode=single)
    O->>A: InvestigationAgent.run()
    A->>T: list_checks(status="fail")
    T->>DB: SELECT * FROM checks WHERE status='fail'
    DB-->>T: Results
    T-->>A: Failed checks data
    A->>T: get_quality_report(stave_id=...)
    T->>DB: Quality metrics query
    DB-->>T: Report data
    T-->>A: Quality report
    A-->>O: Analysis & recommendations
    O-->>U: "3 checks failed on stave 'production-db'..."
```

---

## Quick Start

### Docker Compose (recommended)

```bash
git clone https://github.com/datametronome/datametronome.git
cd datametronome
cp env.example .env

# Start the full stack (API + PostgreSQL + Redis + RabbitMQ + UI)
make up
```

- **API:** http://localhost:8001
- **UI:** http://localhost:3000
- **Login:** `admin` / `admin`

```bash
# Start with Celery workers (adds worker + Beat scheduler containers)
make up-workers

# Run database migrations
make migrate

# View logs
make logs

# Stop everything
make down
```

### Create Your First Check

Create `my_first_stave.yaml`:

```yaml
staves:
  - id: "users-db-001"
    name: "User Database"
    data_source_type: "sqlite"
    connection_config:
      path: "./data/users.db"
    clefs:
      - id: "user-volume"
        name: "Daily User Signups"
        check_type: "row_count"
        config:
          table: "users"
          where: "created_at >= date('now', '-1 day')"
        fail:
          min: 10  # Alert if fewer than 10 signups/day

      - id: "email-quality"
        name: "Email Completeness"
        check_type: "null_percentage"
        config:
          table: "users"
          column: "email"
        warn:
          max: 5  # Warn if more than 5% NULL emails
```

Import and run:

```bash
python -m datametronome_podium.services.stave_yaml_loader my_first_stave.yaml
```

---

## 🔧 Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend | FastAPI + Python 3.13 | REST API, async architecture |
| AI Agents | Pydantic AI | Multi-agent orchestration |
| Frontend | Nuxt 3 + NuxtUI | Dashboard & chat interface |
| Database | PostgreSQL 15+ / SQLite | Primary storage |
| ML Engine | statsmodels + scipy + scikit-learn | Anomaly detection |
| Connectors | asyncpg + aiosqlite | High-performance DB access |
| Scheduling | APScheduler | Automated check execution |

---

## 📐 Data Model

```mermaid
erDiagram
    USERS ||--o{ CHAT_MESSAGES : sends
    STAVES ||--o{ CLEFS : defines
    STAVES ||--o{ CHECKS : produces
    CLEFS ||--o{ CHECKS : executes
    CONVERSATIONS ||--|{ CHAT_MESSAGES : contains
    WORKFLOWS ||--|{ WORKFLOW_EVENTS : logs
```

- **Staves** — Data sources (databases, schemas, tables) to monitor
- **Clefs** — Quality check definitions attached to a stave
- **Checks** — Execution results with pass/warn/fail status

---

## 🧪 Check Types Reference

### Declarative Checks

| Check Type | Description | Use Case |
|------------|-------------|----------|
| `row_count` | Validate table size | Volume monitoring |
| `freshness` | Check data recency | Detect pipeline delays |
| `null_percentage` | Measure completeness | Data quality SLAs |
| `unique_percentage` | Detect duplicates | Deduplication validation |
| `value_range` | Validate bounds | Business rule enforcement |
| `pattern_match` | Regex validation | Format compliance |

### ML / Statistical Checks

| Check Type | Algorithm | Use Case |
|------------|-----------|----------|
| `forecast` | SARIMA | Anomaly detection in time series |
| `data_profile_drift` | KS Test | Distribution shift detection |
| `isolation_forest` | Isolation Forest | Multi-dimensional outlier detection |

---

## 📸 Visual Showcase

### Dashboard Overview
<div align="center">
  <img src="docs/images/dashboard.png" alt="DataMetronome Dashboard" width="800">
  <p><em>Modern Nuxt dashboard with real-time monitoring and metrics</em></p>
</div>

### Quality Checks - Retail Demo
<div align="center">
  <img src="docs/images/quality_checks.png" alt="Quality Checks" width="800">
  <p><em>All 4 checks (Level 1 & 2) for the Retail Production DB</em></p>
</div>

### ML-Powered Anomaly Detection
<div align="center">
  <img src="docs/images/ml_anomalies.png" alt="ML Anomalies" width="800">
  <p><em>Advanced anomaly detection with statistical analysis</em></p>
</div>

---

## Live Demo

A **Retail Demo** is included so you can see DataMetronome in action with synthetic e-commerce data (60 days of order history, volume anomalies, pricing drift).

```bash
# Start the stack
make up

# Import retail demo data (from a separate terminal)
export DB_PATH="$(pwd)/datametronome/podium/data/retail.db"
python showcase/retail_demo/import_to_podium.py

# Run tests to verify everything is working
make test
```

See [docs/TUTORIAL.md](docs/TUTORIAL.md) for a detailed walkthrough.

---

## 📁 Project Structure

```
datametronome/
├── datametronome/
│   ├── podium/          # FastAPI backend (API, agents, scheduler)
│   ├── brain/           # ML models (SARIMA, KS, Isolation Forest)
│   ├── pulse/           # Database connectors (postgres, sqlite)
│   └── plugins/         # Extension system
├── ui-nuxt/             # Nuxt 3 frontend (dashboard, chat widget)
├── showcase/            # Demo scenarios (retail demo)
├── docker-compose.yml   # Docker Compose stack
├── env.example          # Environment template
└── Makefile             # Common tasks
```

---

## 🤝 Contributing

Contributions are welcome! Whether it is a bug fix, new check type, additional connector, or documentation improvement — we appreciate it.

1. **Star the repo** ⭐ to show your support
2. **Read** the [Contributing Guide](CONTRIBUTING.md)
3. **Pick an issue** from [GitHub Issues](https://github.com/datametronome/datametronome/issues)
4. **Submit a PR** with tests

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**🎵 DataMetronome — Making data quality rhythmic, reliable, and intelligent.**

[Get Started](#-quick-start) · [View Demo](#-live-demo) · [Contributing](CONTRIBUTING.md)

</div>
