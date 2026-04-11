"""App settings API schemas."""

from pydantic import BaseModel


class AppSettingResponse(BaseModel):
    key: str
    value: str
    updated_at: str


class AppSettingUpdate(BaseModel):
    value: str
