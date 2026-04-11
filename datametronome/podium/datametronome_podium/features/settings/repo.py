"""App settings repository — encrypted key-value store."""

from __future__ import annotations

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.core.timestamp_utils import now_utc_iso
from datametronome_podium.features.settings.model import AppSettingRow

# Keys that contain secrets and must be encrypted at rest
SENSITIVE_KEYS = frozenset({"ai_api_key"})


class AppSettingsRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def get(self, key: str) -> AppSettingRow | None:
        rows = await self.db.query(
            "SELECT key, value, is_encrypted, updated_at FROM app_settings WHERE key = ?",
            [key],
        )
        if not rows:
            return None
        return AppSettingRow(**dict(rows[0]))

    async def get_all(self) -> list[AppSettingRow]:
        rows = await self.db.query(
            "SELECT key, value, is_encrypted, updated_at FROM app_settings ORDER BY key",
        )
        return [AppSettingRow(**dict(r)) for r in rows]

    async def set(self, key: str, value: str) -> AppSettingRow:
        """Upsert a setting. Sensitive keys are encrypted automatically."""
        from datametronome_podium.core.encryption import encrypt_value

        is_encrypted = key in SENSITIVE_KEYS
        stored_value = encrypt_value(value) if is_encrypted else value
        now = now_utc_iso()

        existing = await self.get(key)
        if existing:
            await self.db.execute(
                "UPDATE app_settings SET value = ?, is_encrypted = ?, updated_at = ? WHERE key = ?",
                [stored_value, is_encrypted, now, key],
            )
        else:
            await self.db.execute(
                "INSERT INTO app_settings (key, value, is_encrypted, updated_at) VALUES (?, ?, ?, ?)",
                [key, stored_value, is_encrypted, now],
            )
        return AppSettingRow(key=key, value=stored_value, is_encrypted=is_encrypted, updated_at=now)

    async def delete(self, key: str) -> bool:
        existing = await self.get(key)
        if not existing:
            return False
        await self.db.execute("DELETE FROM app_settings WHERE key = ?", [key])
        return True

    async def get_decrypted(self, key: str) -> str | None:
        """Get a setting value, decrypting if necessary. Returns None if not found."""
        from datametronome_podium.core.encryption import decrypt_value

        row = await self.get(key)
        if row is None:
            return None
        if row.is_encrypted:
            return decrypt_value(row.value)
        return row.value
