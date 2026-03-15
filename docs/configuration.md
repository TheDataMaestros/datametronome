# Configuration Reference

DataMetronome is configured through environment variables. Copy `env.example` to `.env` at the repository root and adjust the values for your environment.

```bash
cp env.example .env
```

When running with Docker Compose, values in `.env` are loaded automatically. For local development, source the file or export variables manually.

---

## Database

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DATAMETRONOME_DATABASE_URL` | `postgresql://testuser:testpass@localhost:5432/datametronome_test` | Database connection string. PostgreSQL is the default; SQLite is supported as a fallback. |

**PostgreSQL (recommended):**

```
DATAMETRONOME_DATABASE_URL=postgresql://user:password@localhost:5432/datametronome
```

**SQLite (fallback, single-user only):**

```
DATAMETRONOME_DATABASE_URL=sqlite:///./data/datametronome.db
```

> When running inside Docker, the Compose file overrides this to point at the `postgres` service automatically.

---

## Server

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DATAMETRONOME_HOST` | `0.0.0.0` | Host address to bind the API server. |
| `DATAMETRONOME_PORT` | `8001` | Port for the API server. |
| `DATAMETRONOME_DEBUG` | `true` | Enable debug mode. Set to `false` in production. |
| `DATAMETRONOME_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed CORS origins. |
| `DATAMETRONOME_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

---

## Security and Authentication

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DATAMETRONOME_SECRET_KEY` | *(required)* | Secret key for JWT signing. Must be at least 32 characters. Change this in production. |
| `DATAMETRONOME_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | How long access tokens remain valid, in minutes. |

Generate a secure key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## AI Provider

DataMetronome uses an AI agent for chat, intelligent routing, and analysis. Configure which provider to use.

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DATAMETRONOME_AI_PROVIDER` | `ollama` | AI provider: `ollama`, `anthropic`, `openai`, or `gemini`. |
| `DATAMETRONOME_AI_MODEL` | `qwen2.5` | Model name for the main agents. |
| `DATAMETRONOME_AI_API_KEY` | *(none)* | API key for cloud providers. Not needed for Ollama. |
| `DATAMETRONOME_AI_ROUTER_MODEL` | *(same as AI_MODEL)* | Optional cheaper/faster model used only for the routing step. |
| `DATAMETRONOME_AI_BASE_URL` | *(none)* | Base URL for the AI API. Required for Ollama; optional for custom OpenAI-compatible endpoints. |
| `OLLAMA_API_BASE` | `http://localhost:11434` | Legacy Ollama base URL. Used when `AI_PROVIDER=ollama` and `AI_BASE_URL` is unset. |

### Provider Examples

#### Ollama (local, free)

Run models locally with [Ollama](https://ollama.com/). No API key required.

```bash
DATAMETRONOME_AI_PROVIDER=ollama
DATAMETRONOME_AI_MODEL=qwen2.5
DATAMETRONOME_AI_BASE_URL=http://localhost:11434/v1
```

> When running DataMetronome in Docker on macOS or Windows, use `http://host.docker.internal:11434/v1` to reach Ollama on the host machine.

#### Anthropic (Claude)

```bash
DATAMETRONOME_AI_PROVIDER=anthropic
DATAMETRONOME_AI_MODEL=claude-sonnet-4-20250514
DATAMETRONOME_AI_API_KEY=sk-ant-...
DATAMETRONOME_AI_ROUTER_MODEL=claude-haiku-4-5   # optional, cheaper routing
```

#### OpenAI

```bash
DATAMETRONOME_AI_PROVIDER=openai
DATAMETRONOME_AI_MODEL=gpt-4o
DATAMETRONOME_AI_API_KEY=sk-...
```

#### Google Gemini

```bash
DATAMETRONOME_AI_PROVIDER=gemini
DATAMETRONOME_AI_MODEL=gemini-2.0-flash
DATAMETRONOME_AI_API_KEY=your-gemini-api-key
```

---

## Scheduler

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DATAMETRONOME_SCHEDULER_ENABLED` | `true` | Enable the built-in job scheduler. |
| `DATAMETRONOME_SCHEDULER_TIMEZONE` | `UTC` | Timezone for scheduled jobs. |
| `DATAMETRONOME_SCHEDULER_MAX_INSTANCES` | `3` | Maximum concurrent instances of the same job. |
| `DATAMETRONOME_SCHEDULER_MAX_WORKERS` | `10` | Maximum worker threads for job execution. |

---

## Job Queue

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DATAMETRONOME_JOB_QUEUE_SIZE` | `1000` | Maximum number of jobs in the queue. |
| `DATAMETRONOME_WORKER_POOL_SIZE` | `4` | Number of workers processing the queue. |

---

## Metrics and Analytics

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DATAMETRONOME_METRICS_ENABLED` | `true` | Enable metrics collection. |
| `DATAMETRONOME_METRICS_RETENTION_DAYS` | `90` | How many days to retain historical metrics. |

---

## Observability

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `LOGFIRE_TOKEN` | *(none)* | [Logfire](https://logfire.pydantic.dev/) write token. When set, traces are sent to Logfire cloud for observability. |

---

## UI (Nuxt Frontend)

These variables configure the Nuxt frontend. They are set automatically in Docker Compose.

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `NUXT_PUBLIC_API_BASE` | `http://localhost:8001/api/v1` | Base URL for the Podium REST API (used by the frontend). |
| `NUXT_PUBLIC_PODIUM_API_BASE` | `http://localhost:8001` | Base URL for the Podium server (used for WebSocket and non-API calls). |

---

## Production Checklist

Before deploying to production, ensure the following:

- [ ] `DATAMETRONOME_SECRET_KEY` is a unique, randomly generated value (at least 32 characters)
- [ ] `DATAMETRONOME_DEBUG` is set to `false`
- [ ] `DATAMETRONOME_DATABASE_URL` points to a production PostgreSQL instance
- [ ] `DATAMETRONOME_AI_API_KEY` is set if using a cloud AI provider
- [ ] `DATAMETRONOME_ALLOWED_ORIGINS` lists only your production domain(s)
- [ ] Default admin password has been changed
