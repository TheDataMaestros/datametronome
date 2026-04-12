"""App settings API router — admin-only installation config."""

from fastapi import APIRouter, Depends, HTTPException

from datametronome_podium.core.auth import require_admin
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.encryption import MASKED_VALUE
from datametronome_podium.features.settings.repo import AppSettingsRepo, SENSITIVE_KEYS
from datametronome_podium.features.settings.schema import AppSettingResponse, AppSettingUpdate

router = APIRouter()

# Keys that the UI is allowed to read/write
ALLOWED_KEYS = frozenset({
    "ai_provider",
    "ai_model",
    "ai_api_key",
    "ai_router_model",
    "ai_heavy_model",
    "ai_base_url",
})


def _repo() -> AppSettingsRepo:
    return AppSettingsRepo(get_executor())


def _mask_if_sensitive(key: str, value: str) -> str:
    return MASKED_VALUE if key in SENSITIVE_KEYS else value


@router.get("/", response_model=list[AppSettingResponse])
async def list_settings(_user: dict = Depends(require_admin)):
    """List all app settings (sensitive values masked)."""
    repo = _repo()
    rows = await repo.get_all()
    return [
        AppSettingResponse(
            key=r.key,
            value=_mask_if_sensitive(r.key, r.value),
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/{key}", response_model=AppSettingResponse)
async def get_setting(key: str, _user: dict = Depends(require_admin)):
    """Get a single setting (sensitive values masked)."""
    repo = _repo()
    row = await repo.get(key)
    if not row:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return AppSettingResponse(
        key=row.key,
        value=_mask_if_sensitive(row.key, row.value),
        updated_at=row.updated_at,
    )


@router.put("/{key}", response_model=AppSettingResponse)
async def set_setting(key: str, body: AppSettingUpdate, _user: dict = Depends(require_admin)):
    """Create or update a setting. Only allowed keys are accepted."""
    if key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown setting key: '{key}'")
    # If user sends MASKED_VALUE, they didn't change the secret — skip update
    if body.value == MASKED_VALUE:
        repo = _repo()
        row = await repo.get(key)
        if not row:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        return AppSettingResponse(key=row.key, value=MASKED_VALUE, updated_at=row.updated_at)
    repo = _repo()
    row = await repo.set(key, body.value)
    return AppSettingResponse(
        key=row.key,
        value=_mask_if_sensitive(row.key, row.value),
        updated_at=row.updated_at,
    )


@router.delete("/{key}")
async def delete_setting(key: str, _user: dict = Depends(require_admin)):
    """Delete a setting (reverts to env var fallback)."""
    repo = _repo()
    deleted = await repo.delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return {"message": f"Setting '{key}' deleted"}
