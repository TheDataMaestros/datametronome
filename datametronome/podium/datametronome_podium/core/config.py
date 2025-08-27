"""
Configuration management for DataMetronome Podium.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with modern type hints and validation."""
    
    # Application
    app_name: str = "DataMetronome Podium"
    version: str = "0.1.0"
    debug: bool = Field(default=False, env="DATAMETRONOME_DEBUG")
    
    # Server
    host: str = Field(default="0.0.0.0", env="DATAMETRONOME_HOST")
    port: int = Field(default=8000, env="DATAMETRONOME_PORT", ge=1, le=65535)
    
    # Security
    secret_key: str = Field(default="test-secret-key-for-development-only-32-chars", env="DATAMETRONOME_SECRET_KEY", min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, env="DATAMETRONOME_ACCESS_TOKEN_EXPIRE_MINUTES", ge=1)
    
    # Database
    database_url: str = Field(default="sqlite:///./datametronome.db", env="DATAMETRONOME_DATABASE_URL")
    
    # CORS
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        env="DATAMETRONOME_ALLOWED_ORIGINS"
    )
    
    # Logging
    log_level: str = Field(default="INFO", env="DATAMETRONOME_LOG_LEVEL")
    
    # Scheduler
    scheduler_enabled: bool = Field(default=True, env="DATAMETRONOME_SCHEDULER_ENABLED")
    scheduler_timezone: str = Field(default="UTC", env="DATAMETRONOME_SCHEDULER_TIMEZONE")
    
    # Job Queue
    job_queue_size: int = Field(default=1000, env="DATAMETRONOME_JOB_QUEUE_SIZE", ge=1)
    worker_pool_size: int = Field(default=4, env="DATAMETRONOME_WORKER_POOL_SIZE", ge=1)
    
    # Metrics
    metrics_enabled: bool = Field(default=True, env="DATAMETRONOME_METRICS_ENABLED")
    metrics_retention_days: int = Field(default=90, env="DATAMETRONOME_METRICS_RETENTION_DAYS", ge=1)
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is supported."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    @field_validator('allowed_origins')
    @classmethod
    def validate_allowed_origins(cls, v: list[str]) -> list[str]:
        """Validate CORS origins are valid URLs."""
        if not v:
            raise ValueError('allowed_origins cannot be empty')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = "DATAMETRONOME_"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
