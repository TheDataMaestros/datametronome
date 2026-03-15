# Getting Started with DataMetronome

DataMetronome is a data quality monitoring platform with AI-powered chat, automated checks, scheduling, and analytics. This guide walks you through setup and your first steps.

## Docker Quick Start (Recommended)

The fastest way to run DataMetronome is with Docker Compose. This starts PostgreSQL, the Podium API, and (optionally) the Nuxt UI in a single command.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2+

### Steps

```bash
# Clone the repository
git clone https://github.com/datametronome/datametronome.git
cd datametronome

# Create your environment file
cp env.example .env

# Start the API + PostgreSQL
docker compose up -d

# (Optional) Start the UI as well
docker compose --profile full up -d
```

Once the containers are healthy:

| Service    | URL                        |
| ---------- | -------------------------- |
| Podium API | http://localhost:8001      |
| API Docs   | http://localhost:8001/docs |
| UI         | http://localhost:3000      |

**Default credentials:** `admin` / `admin`

### Verify It Works

```bash
# Check the health endpoint
curl http://localhost:8001/health

# View logs
docker compose logs -f podium
```

---

## Local Development Setup

If you prefer to run services directly on your machine, follow the steps below.

### Prerequisites

- Python 3.13+
- Node.js 20+ (for the UI)
- PostgreSQL 15+ **or** use Docker for the database only

### Backend (Podium API)

```bash
# Start PostgreSQL via Docker (if you don't have a local instance)
docker compose up -d postgres

# Create a virtual environment
cd datametronome/podium
python3.13 -m venv .venv
source .venv/bin/activate

# Return to the repo root and install all packages
cd ../..
.venv/bin/pip install -e ./datametronome/pulse/core \
                      -e ./datametronome/pulse/sqlite \
                      -e ./datametronome/pulse/postgres \
                      -e ./datametronome/brain/base \
                      -e ./datametronome/podium

# Copy the env file (if you haven't already)
cp env.example .env

# Run database migrations
cd datametronome/podium
DATABASE_URL="${DATAMETRONOME_DATABASE_URL}" alembic upgrade head

# Start the API
cd ../..
.venv/bin/python -m datametronome_podium.main
```

The API is now available at http://localhost:8001.

### Frontend (Nuxt UI)

```bash
cd ui-nuxt
npm install
NUXT_PUBLIC_API_BASE=http://localhost:8001/api/v1 \
NUXT_PUBLIC_PODIUM_API_BASE=http://localhost:8001 \
npm run dev
```

The UI is now available at http://localhost:3000.

### Running Tests

```bash
cd datametronome/podium
.venv/bin/python -m pytest tests/ -v --timeout=10
```

---

## First Steps After Setup

### 1. Log In

Open http://localhost:3000 (or http://localhost:8001/docs for the API) and log in with `admin` / `admin`.

### 2. Try the AI Chat

Navigate to the Chat section and ask a question like:

> "What data sources do I have?"

The AI agent inspects your connected data sources and returns a summary.

### 3. Add a Data Source

A data source (called a **Stave**) represents a database you want to monitor. Add one through the UI or the API:

```bash
curl -X POST http://localhost:8001/api/v1/staves/ \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My PostgreSQL",
    "db_type": "postgresql",
    "connection_string": "postgresql://user:pass@host:5432/mydb"
  }'
```

### 4. Create a Quality Check

A **Clef** defines what to check. For example, verify that a table has rows:

```bash
curl -X POST http://localhost:8001/api/v1/clefs/ \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "orders_not_empty",
    "stave_id": 1,
    "check_type": "row_count",
    "query": "SELECT COUNT(*) FROM orders",
    "threshold_min": 1
  }'
```

### 5. Run Checks

Execute your checks manually or set up a schedule. Results are stored as **Check Results** and surfaced in the analytics dashboard.

---

## Using Make Commands

The project includes a `Makefile` with helpful shortcuts:

```bash
make help              # Show all available commands
make setup-env         # Create .env from env.example
make docker-up         # Start API + PostgreSQL
make docker-up-full    # Start API + PostgreSQL + UI
make docker-down       # Stop all services
make docker-build      # Rebuild Docker images
make docker-prototype  # Build and start everything
```

---

## Next Steps

- [Configuration Reference](./configuration.md) -- all environment variables explained
- [Development Guide](./development.md) -- project structure, testing, and contributing
