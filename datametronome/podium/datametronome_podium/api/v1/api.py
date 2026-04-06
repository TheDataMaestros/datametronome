"""
Main API router for DataMetronome Podium v1.

Uses feature-based routers for CRUD (staves, clefs, checks).
Complex endpoints (auth, chat, actions, scheduler) stay in api/v1/endpoints/.

All routers except /auth require authentication via get_current_user.
"""

from fastapi import APIRouter, Depends

from datametronome_podium.api.v1.endpoints.auth import get_current_user

# Feature-based routers (new architecture)
from datametronome_podium.features.staves.router import router as staves_router
from datametronome_podium.features.clefs.router import router as clefs_router
from datametronome_podium.features.checks.router import router as checks_router
from datametronome_podium.features.insights.router import router as insights_router
from datametronome_podium.features.user_memory.router import router as user_memory_router

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

# Auth dependency applied at router level — every endpoint below requires a valid JWT
# except /auth (login + register must be public)
_auth_deps = [Depends(get_current_user)]

# Feature-based routers (CRUD via QueryExecutor + Repos)
api_router.include_router(staves_router, prefix="/staves", tags=["data sources"])
api_router.include_router(clefs_router, prefix="/clefs", tags=["rule sets"])
api_router.include_router(checks_router, prefix="/checks", tags=["checks"])
api_router.include_router(insights_router, prefix="/insights", tags=["intelligence"], dependencies=_auth_deps)
api_router.include_router(user_memory_router, prefix="/user/memory", tags=["user memory"])

# Auth endpoints (public — login/register don't require a token)
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# All other endpoints require authentication
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"], dependencies=_auth_deps)
api_router.include_router(reports.router, prefix="/reports", tags=["reporting"], dependencies=_auth_deps)
api_router.include_router(
    stave_actions.router, prefix="/stave-actions", tags=["stave actions"], dependencies=_auth_deps,
)
api_router.include_router(clef_actions.router, prefix="/clefs", tags=["clef actions"], dependencies=_auth_deps)
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"], dependencies=_auth_deps)
api_router.include_router(
    import_config.router, prefix="/config", tags=["configuration"], dependencies=_auth_deps,
)
api_router.include_router(trends.router, prefix="/trends", tags=["trends"], dependencies=_auth_deps)
api_router.include_router(chat.router, prefix="/chat", tags=["chat"], dependencies=_auth_deps)
