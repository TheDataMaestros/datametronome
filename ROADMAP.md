# 🎵 DataMetronome Roadmap

**Last Updated**: September 2026
**Status**: Active Development

> High-level direction. For the current architecture see
> [docs/architecture.md](docs/architecture.md); for design specs and
> implementation plans see `docs/superpowers/`.

---

## 🎯 Vision

Transform DataMetronome into the **leading open-source data quality and anomaly
detection platform**, providing enterprise-grade monitoring with a delightful
developer experience.

---

## ✅ Shipped

### Core platform
- Podium FastAPI backend organised into feature slices
- Single database access path (`QueryExecutor` / `QueryAdapter`), Alembic migrations
- Nuxt 3 frontend with dashboard, staves, clefs, checks, trends and insights pages
- JWT auth with role-based access control (`admin` / `editor` / `viewer`)
- Encryption at rest for connector credentials and other sensitive settings
- Health endpoint, Prometheus metrics, structured logging, distributed tracing

### Connectors (Pulse)
- `core` — shared protocol and base classes
- `postgres` (asyncpg), `postgres-psycopg3` (Redshift), `s3` (DuckDB)
- `sqlite`
- `bigquery`
- `dbt` — read-only, reads manifest/run_results from a local project or dbt Cloud

### Execution
- Celery workers with RabbitMQ broker and Redis result backend
- celery-redbeat scheduler
- Pluggable dispatch: `inline`, `celery`, `remote`
- Circuit breaker that pauses staves after consecutive failures

### AI
- Pydantic AI multi-agent orchestration: router classifies intent, orchestrator
  dispatches to config / investigation / report / insight agents
- Data intelligence layer — domain classification via archetype templates
- Per-user memory layer feeding agent context

### Operations
- CI on Python 3.12 and 3.13: type check plus full backend and connector suites
- Frontend lint and build in CI
- Tag-driven PyPI publication for the Pulse packages
- Docker Compose for dev, showcase and production topologies

---

## 🔭 Next

Ordered by value, not by date. No promises attached to quarters.

### Alerting beyond a single webhook
A global webhook now fires on failed checks. What is missing: per-stave routing,
severity thresholds, retry and dedupe, and first-class Slack/email/PagerDuty
channels.

### Test depth where it is thin
- Frontend coverage is two service specs. CI still only lints and builds the UI.
- `pulse/bigquery` ships fixtures, not tests that hit BigQuery.

### More connectors
The picker only offers types the factory can build: postgres, redshift,
sqlite, bigquery, s3, dbt. MySQL, MongoDB, Snowflake and Redis are not
offered. Add them as Pulse packages when someone needs them.

### Packaging
Only `pulse/core` and `pulse/sqlite` carry a CHANGELOG. The rest need one
before the next release goes out.

### Streaming and richer ML
Real-time updates over WebSockets, and anomaly detection beyond the current
Isolation Forest and SARIMA models.

---

## 📊 Success Metrics

### Technical
- **Test Coverage**: > 90% for all packages
- **Performance**: < 100ms API response time (p95)
- **Reliability**: 99.9% uptime for hosted services
- **Security**: Zero critical vulnerabilities

### Community
- **Documentation**: 100% API coverage
- **Response Time**: < 48h for issues

---

## 💡 Feature Prioritization Framework

**Priority Scoring** = (Impact × Adoption) / (Effort × Risk)

- **Impact**: How much value does it add? (1-5)
- **Adoption**: How many users benefit? (1-5)
- **Effort**: How long to implement? (1-5)
- **Risk**: How risky is it? (1-5)

---

## 🤝 How to Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

**Areas where we need help:**
- 📝 Documentation and tutorials
- 🐛 Bug fixes and testing
- 🎨 UI/UX improvements
- 🔌 New database connectors
- 🤖 ML algorithm implementations
- 🌍 Internationalization (i18n)

---

## 📞 Feedback

Have ideas or suggestions?
- Open a [GitHub Discussion](https://github.com/datametronome/datametronome/discussions)
- Join our community chat
- Email: roadmap@datametronome.dev

---

**🎵 Let's make data quality better for everyone!**
