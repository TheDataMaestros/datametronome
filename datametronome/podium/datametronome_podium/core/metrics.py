"""
Prometheus metrics for DataMetronome Podium.

Provides application metrics for monitoring and observability.
"""

import logging

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

logger = logging.getLogger(__name__)

# Create a custom registry to avoid conflicts
registry = CollectorRegistry()

# =============================================================================
# Application Info
# =============================================================================

app_info = Info(
    "datametronome_podium",
    "DataMetronome Podium application information",
    registry=registry,
)
app_info.info({"version": "0.1.0", "service": "podium-api"})

# =============================================================================
# HTTP Metrics
# =============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry,
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed",
    ["method", "endpoint"],
    registry=registry,
)

# =============================================================================
# Database Metrics
# =============================================================================

database_connections = Gauge(
    "database_connections",
    "Number of active database connections",
    ["state"],  # 'active', 'idle'
    registry=registry,
)

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],  # 'read', 'write', 'execute'
    registry=registry,
)

database_queries_total = Counter(
    "database_queries_total",
    "Total database queries",
    ["operation", "status"],  # operation: read/write, status: success/error
    registry=registry,
)

# =============================================================================
# Check Run Metrics
# =============================================================================

check_runs_total = Counter(
    "check_runs_total",
    "Total data quality check runs",
    ["clef_id", "status"],  # status: success, failed, error
    registry=registry,
)

check_run_duration_seconds = Histogram(
    "check_run_duration_seconds",
    "Check run duration in seconds",
    ["clef_id"],
    registry=registry,
)

anomalies_detected_total = Counter(
    "anomalies_detected_total",
    "Total anomalies detected",
    ["clef_id", "severity"],  # severity: low, medium, high, critical
    registry=registry,
)

# =============================================================================
# System Metrics
# =============================================================================

system_health = Gauge(
    "system_health",
    "System health status (1=healthy, 0=unhealthy)",
    ["component"],  # component: database, scheduler, api
    registry=registry,
)

active_clefs = Gauge(
    "active_clefs", "Number of active data quality checks", registry=registry
)

active_staves = Gauge(
    "active_staves", "Number of active data sources", registry=registry
)

scheduler_jobs = Gauge("scheduler_jobs", "Number of scheduled jobs", registry=registry)

# =============================================================================
# Chat / Agent Metrics (multi-agent Phase 0)
# =============================================================================

chat_requests_total = Counter(
    "chat_requests_total",
    "Total chat/agent requests",
    ["status", "intent"],  # status: success, error; intent: quick, config, etc.
    registry=registry,
)

chat_request_duration_seconds = Histogram(
    "chat_request_duration_seconds",
    "Chat request duration in seconds",
    ["intent"],
    registry=registry,
)

chat_tool_calls_total = Counter(
    "chat_tool_calls_total",
    "Total tool calls made by agent",
    ["tool_name"],
    registry=registry,
)

# =============================================================================
# Business Metrics
# =============================================================================

users_total = Gauge(
    "users_total",
    "Total number of users",
    ["status"],  # status: active, inactive
    registry=registry,
)

# =============================================================================
# Helper Functions
# =============================================================================


def get_metrics_content() -> tuple[bytes, str]:
    """
    Get Prometheus metrics in the correct format.

    Returns:
        Tuple of (metrics_content, content_type)
    """
    return generate_latest(registry), CONTENT_TYPE_LATEST


async def update_system_metrics():
    """Update system-level metrics from database."""
    try:
        from .database import get_executor

        executor = get_executor()

        # Count active staves
        staves = await executor.query(
            "SELECT COUNT(*) as count FROM staves WHERE is_active = 1"
        )
        if staves:
            active_staves.set(staves[0].get("count", 0))

        # Count active clefs
        clefs = await executor.query(
            "SELECT COUNT(*) as count FROM clefs WHERE is_active = 1"
        )
        if clefs:
            active_clefs.set(clefs[0].get("count", 0))

        # Count users
        users = await executor.query(
            "SELECT COUNT(*) as count, is_active FROM users GROUP BY is_active"
        )
        for user_group in users:
            status = "active" if user_group.get("is_active") else "inactive"
            users_total.labels(status=status).set(user_group.get("count", 0))

        # Update scheduler jobs count
        from .scheduler import get_scheduler_status  # ty: ignore[unresolved-import]

        scheduler_status = get_scheduler_status()
        if scheduler_status and scheduler_status.get("status") == "running":
            scheduler_jobs.set(scheduler_status.get("job_count", 0))

        logger.debug("System metrics updated successfully")

    except Exception as e:
        logger.error(f"Failed to update system metrics: {e}")


def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """
    Record HTTP request metrics.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        status_code: HTTP status code
        duration: Request duration in seconds
    """
    http_requests_total.labels(
        method=method, endpoint=endpoint, status=str(status_code)
    ).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
        duration
    )


def record_chat_request(
    status: str,
    duration_seconds: float,
    intent: str = "unknown",
    tool_calls: list | None = None,
):
    """
    Record chat/agent request metrics.

    Args:
        status: success or error
        duration_seconds: Request duration
        intent: Inferred intent (Phase 0: unknown until router)
        tool_calls: List of tool call dicts with 'name' key
    """
    chat_requests_total.labels(status=status, intent=intent).inc()
    chat_request_duration_seconds.labels(intent=intent).observe(duration_seconds)
    if tool_calls:
        for tc in tool_calls:
            name = tc.get("name", "unknown") if isinstance(tc, dict) else "unknown"
            chat_tool_calls_total.labels(tool_name=name).inc()


def set_component_health(component: str, is_healthy: bool):
    """
    Set health status for a system component.

    Args:
        component: Component name (database, scheduler, api)
        is_healthy: True if healthy, False otherwise
    """
    system_health.labels(component=component).set(1 if is_healthy else 0)


