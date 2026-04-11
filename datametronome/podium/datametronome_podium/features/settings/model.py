"""App settings model — single key-value row."""

from pydantic import BaseModel


class AppSettingRow(BaseModel):
    key: str
    value: str = ""
    is_encrypted: bool = False
    updated_at: str = ""
