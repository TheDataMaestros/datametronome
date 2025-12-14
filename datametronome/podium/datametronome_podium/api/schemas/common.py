"""
Common schemas and validation helpers for API responses.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Resource not found",
                "error_code": "NOT_FOUND",
                "status_code": 404,
            }
        }
    )

    detail: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Resource not found", "Validation error"],
    )
    error_code: str | None = Field(
        None,
        description="Machine-readable error code",
        examples=["NOT_FOUND", "VALIDATION_ERROR", "AUTH_FAILED"],
    )
    status_code: int = Field(
        ..., description="HTTP status code", examples=[400, 401, 404, 500]
    )


class SuccessResponse(BaseModel):
    """Standard success response schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Operation completed successfully",
                "status": "success",
            }
        }
    )

    message: str = Field(
        ...,
        description="Success message",
        examples=["Resource created successfully", "Update completed"],
    )
    status: str = Field("success", description="Operation status", examples=["success"])


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 50,
                "pages": 2,
            }
        }
    )

    items: list[T] = Field(..., description="List of items for current page")
    total: int = Field(
        ..., description="Total number of items across all pages", examples=[100]
    )
    page: int = Field(..., description="Current page number (1-indexed)", examples=[1])
    page_size: int = Field(..., description="Number of items per page", examples=[50])
    pages: int = Field(..., description="Total number of pages", examples=[2])


class HealthCheckResponse(BaseModel):
    """Health check response schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "timestamp": "2024-10-03T10:00:00Z",
                "service": "datametronome-podium",
                "checks": {
                    "database": {
                        "status": "healthy",
                        "message": "Database connection OK",
                    },
                    "scheduler": {"status": "healthy", "message": "Scheduler running"},
                },
            }
        }
    )

    status: str = Field(
        ...,
        description="Overall system health status",
        examples=["healthy", "degraded", "unhealthy"],
    )
    version: str = Field(..., description="Application version", examples=["0.1.0"])
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of health check",
        examples=["2024-10-03T10:00:00Z"],
    )
    service: str = Field(
        ..., description="Service name", examples=["datametronome-podium"]
    )
    checks: dict[str, dict[str, str]] = Field(
        ..., description="Individual component health checks"
    )
