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
    # Logging
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False, env="DATAMETRONOME_DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", env="DATAMETRONOME_HOST")
    port: int = Field(default=8001, env="DATAMETRONOME_PORT", ge=1, le=65535)

    # Security
    secret_key: str = Field(
        default="test-secret-key-for-development-only-32-chars",
        env="DATAMETRONOME_SECRET_KEY",
        min_length=32,
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(
        default=30,
        env="DATAMETRONOME_ACCESS_TOKEN_EXPIRE_MINUTES",
        ge=1,
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./data/datametronome.db",
        env="DATAMETRONOME_DATABASE_URL",
    )

    # CORS
    allowed_origins: list[str] | str = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        env="DATAMETRONOME_ALLOWED_ORIGINS",
    )

    # Scheduler
    scheduler_enabled: bool = Field(default=True, env="DATAMETRONOME_SCHEDULER_ENABLED")
    scheduler_timezone: str = Field(
        default="UTC",
        env="DATAMETRONOME_SCHEDULER_TIMEZONE",
    )
    scheduler_max_instances: int = Field(
        default=3,
        env="DATAMETRONOME_SCHEDULER_MAX_INSTANCES",
        ge=1,
    )
    scheduler_max_workers: int = Field(
        default=10,
        env="DATAMETRONOME_SCHEDULER_MAX_WORKERS",
        ge=1,
    )

    # Job Queue
    job_queue_size: int = Field(default=1000, env="DATAMETRONOME_JOB_QUEUE_SIZE", ge=1)
    worker_pool_size: int = Field(default=4, env="DATAMETRONOME_WORKER_POOL_SIZE", ge=1)

    # Metrics
    metrics_enabled: bool = Field(default=True, env="DATAMETRONOME_METRICS_ENABLED")
    metrics_retention_days: int = Field(
        default=90,
        env="DATAMETRONOME_METRICS_RETENTION_DAYS",
        ge=1,
    )

    # AI Agent Configuration
    ai_provider: str = Field(
        default="ollama",
        description="AI provider: anthropic | openai | gemini | ollama",
        validation_alias="DATAMETRONOME_AI_PROVIDER",
    )
    ai_model: str = Field(
        default="qwen2.5",
        description="Model name for the main agents (e.g. claude-sonnet-4-6, gpt-4o, qwen2.5)",
        validation_alias="DATAMETRONOME_AI_MODEL",
    )
    ai_api_key: str = Field(
        default="",
        description="API key for the AI provider (not needed for Ollama)",
        validation_alias="DATAMETRONOME_AI_API_KEY",
    )
    ai_router_model: str | None = Field(
        default=None,
        description="Optional cheaper model for the router agent (e.g. claude-haiku-4-5). If unset, uses ai_model.",
        validation_alias="DATAMETRONOME_AI_ROUTER_MODEL",
    )
    ai_base_url: str | None = Field(
        default=None,
        description="Custom base URL (required for Ollama: http://localhost:11434/v1)",
        validation_alias="DATAMETRONOME_AI_BASE_URL",
    )
    ollama_api_base: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL (legacy compat). Used when ai_provider=ollama and ai_base_url is unset.",
        validation_alias="OLLAMA_API_BASE",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is supported."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, v: list[str] | str) -> list[str]:
        """Validate and parse CORS origins."""
        if isinstance(v, str):
            # Handle wildcard
            if v.strip() == "*":
                return ["*"]
            # Handle JSON-like string if passed
            cleaned = v.strip()
            if cleaned.startswith("[") and cleaned.endswith("]"):
                import json

                try:
                    return json.loads(cleaned)
                except:
                    pass
            # Split by comma
            v = [origin.strip() for origin in cleaned.split(",") if origin.strip()]

        if not v:
            # Default to localhost if empty in dev
            return ["http://localhost:3000"]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = "DATAMETRONOME_"
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def validate_production_config() -> tuple[list[str], list[str]]:
    """
    Validate critical configuration for production deployment.

    Returns:
        List of validation warnings/errors
    """
    warnings = []
    errors = []

    # Check secret key is not default
    if settings.secret_key == "test-secret-key-for-development-only-32-chars":
        if not settings.debug:
            errors.append(
                "⚠️  CRITICAL: Using default SECRET_KEY in production! "
                "Set DATAMETRONOME_SECRET_KEY to a secure random value. "
                "Generate one with: openssl rand -hex 32",
            )
        else:
            warnings.append(
                "ℹ️  Using default SECRET_KEY (OK for development, "
                "but change for production)",
            )

    # Check debug mode in production
    if settings.debug:
        warnings.append(
            "⚠️  Debug mode is enabled. Disable in production by setting "
            "DATAMETRONOME_DEBUG=false",
        )

    # Check CORS origins
    if (
        "*" in settings.allowed_origins
        or "http://localhost" in str(settings.allowed_origins).lower()
    ):
        if not settings.debug:
            warnings.append(
                "⚠️  CORS allows localhost or all origins (*). "
                "Restrict DATAMETRONOME_ALLOWED_ORIGINS in production",
            )

    # Check database URL
    if "sqlite" in settings.database_url.lower():
        if not settings.debug:
            warnings.append(
                "ℹ️  Using SQLite database. Consider PostgreSQL for production "
                "for better performance and scalability",
            )

    # Check log level
    if settings.log_level == "DEBUG" and not settings.debug:
        warnings.append(
            "⚠️  Log level is DEBUG in non-debug mode. "
            "This may impact performance and expose sensitive information",
        )

    # Check access token expiry
    if settings.access_token_expire_minutes > 1440:  # 24 hours
        warnings.append(
            f"⚠️  Access token expires in {settings.access_token_expire_minutes} minutes (>24h). "
            "Consider shorter expiration for security",
        )

    return errors, warnings


def print_startup_banner():
    """Print startup banner with configuration info."""
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          🎵  DataMetronome Podium API v{settings.version}              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

Configuration:
  📍 Host:        {settings.host}:{settings.port}
  🔧 Debug:       {settings.debug}
  📊 Metrics:     {settings.metrics_enabled}
  ⏰ Scheduler:   {settings.scheduler_enabled}
  📝 Log Level:   {settings.log_level}
  🗄️  Database:    {settings.database_url.split('://')[0]}://***
  🌐 CORS:        {len(settings.allowed_origins)} origins

Endpoints:
  📚 Docs:        http://{settings.host}:{settings.port}/docs
  🔍 Health:      http://{settings.host}:{settings.port}/health
  📊 Metrics:     http://{settings.host}:{settings.port}/metrics
"""
    print(banner)


def validate_and_report_config():
    """
    Validate configuration and print report.

    Raises:
        SystemExit: If critical configuration errors are found
    """
    errors, warnings = validate_production_config()

    # Print warnings
    if warnings:
        print("\n⚠️  Configuration Warnings:")
        for warning in warnings:
            print(f"  {warning}")

    # Print errors and exit if critical
    if errors:
        print("\n❌ Configuration Errors:")
        for error in errors:
            print(f"  {error}")
        print("\nPlease fix the above errors before starting the application.")
        raise SystemExit(1)

    # Print success message
    if not warnings and not errors:
        print("\n✅ Configuration validation passed")
    elif not errors:
        print("\n✅ Configuration validated (with warnings)")

    print()  # Empty line for readability
