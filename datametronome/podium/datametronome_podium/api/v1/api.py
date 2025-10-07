"""
Main API router for DataMetronome Podium v1.
"""

from fastapi import APIRouter

from .endpoints import auth, staves, clefs, checks, metrics, reports, stave_actions, clef_actions, scheduler

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(staves.router, prefix="/staves", tags=["data sources"])
api_router.include_router(clefs.router, prefix="/clefs", tags=["rule sets"])
api_router.include_router(checks.router, prefix="/checks", tags=["checks"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(reports.router, prefix="/reports", tags=["reporting"])
api_router.include_router(stave_actions.router, prefix="/stave-actions", tags=["stave actions"])
api_router.include_router(clef_actions.router, prefix="/clefs", tags=["clef actions"])
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"])
