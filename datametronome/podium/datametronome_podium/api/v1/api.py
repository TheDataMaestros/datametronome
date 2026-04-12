"""
Main API router for DataMetronome Podium v1.

All endpoints live in features/*/ slices.
All routers except /auth require authentication via get_current_user.
"""

from fastapi import APIRouter, Depends

from datametronome_podium.core.auth import get_current_user

# Feature-based routers
from datametronome_podium.features.analytics.router import router as analytics_router
from datametronome_podium.features.auth.router import router as auth_router
from datametronome_podium.features.chat.router import router as chat_router
from datametronome_podium.features.checks.router import router as checks_router
from datametronome_podium.features.clefs.router import router as clefs_router
from datametronome_podium.features.insights.router import router as insights_router
from datametronome_podium.features.metrics.router import router as metrics_router
from datametronome_podium.features.reports.router import router as reports_router
from datametronome_podium.features.settings.router import router as settings_router
from datametronome_podium.features.staves.router import router as staves_router
from datametronome_podium.features.trends.router import router as trends_router
from datametronome_podium.features.user_memory.router import router as user_memory_router
from datametronome_podium.features.users.router import router as users_router

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
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])

# All other endpoints require authentication
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"], dependencies=_auth_deps)
api_router.include_router(reports_router, prefix="/reports", tags=["reporting"], dependencies=_auth_deps)
api_router.include_router(trends_router, prefix="/trends", tags=["trends"], dependencies=_auth_deps)
api_router.include_router(chat_router, prefix="/chat", tags=["chat"], dependencies=_auth_deps)
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"], dependencies=_auth_deps)
api_router.include_router(settings_router, prefix="/settings", tags=["settings"], dependencies=_auth_deps)
api_router.include_router(users_router, prefix="/users", tags=["users"], dependencies=_auth_deps)
