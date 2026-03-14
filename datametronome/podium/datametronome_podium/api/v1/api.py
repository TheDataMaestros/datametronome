"""
Main API router for DataMetronome Podium v1.

Uses feature-based routers for CRUD (staves, clefs, checks).
Complex endpoints (auth, chat, actions, scheduler) stay in api/v1/endpoints/.
"""

from fastapi import APIRouter

# Feature-based routers (new architecture)
from datametronome_podium.features.staves.router import router as staves_router
from datametronome_podium.features.clefs.router import router as clefs_router
from datametronome_podium.features.checks.router import router as checks_router

# Complex endpoints that stay in api/v1/endpoints/ (not yet migrated)
from .endpoints import (
    auth,
    chat,
    clef_actions,
    import_config,
    metrics,
    reports,
    scheduler,
    stave_actions,
    trends,
)

api_router = APIRouter()

# Feature-based routers (CRUD via QueryExecutor + Repos)
api_router.include_router(staves_router, prefix="/staves", tags=["data sources"])
api_router.include_router(clefs_router, prefix="/clefs", tags=["rule sets"])
api_router.include_router(checks_router, prefix="/checks", tags=["checks"])

# Complex endpoints (auth, orchestration, actions, scheduling)
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(reports.router, prefix="/reports", tags=["reporting"])
api_router.include_router(
    stave_actions.router, prefix="/stave-actions", tags=["stave actions"]
)
api_router.include_router(clef_actions.router, prefix="/clefs", tags=["clef actions"])
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"])
api_router.include_router(
    import_config.router, prefix="/config", tags=["configuration"]
)
api_router.include_router(trends.router, prefix="/trends", tags=["trends"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
