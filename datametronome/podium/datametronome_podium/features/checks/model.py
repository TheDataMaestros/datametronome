"""Check domain model."""
from pydantic import BaseModel


class Check(BaseModel):
    id: str
    stave_id: str
    clef_id: str
    check_type: str
    status: str
    message: str | None = None
    details: str | None = None  # JSON string
    timestamp: str
    execution_time: float | None = None
    anomalies_count: int = 0
    severity: str = "medium"
