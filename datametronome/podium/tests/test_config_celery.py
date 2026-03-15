"""Tests for Celery/Redis configuration fields."""
import pytest
from datametronome_podium.core.config import Settings


def test_celery_broker_url_default():
    s = Settings(secret_key="x" * 32)
    assert s.celery_broker_url == "amqp://guest:guest@rabbitmq:5672//"


def test_celery_result_backend_default():
    s = Settings(secret_key="x" * 32)
    assert s.celery_result_backend == "redis://redis:6379/0"


def test_redis_url_default():
    s = Settings(secret_key="x" * 32)
    assert s.redis_url == "redis://redis:6379/0"


def test_celery_concurrency_default():
    s = Settings(secret_key="x" * 32)
    assert s.celery_concurrency == 4


def test_celery_config_from_env(monkeypatch):
    monkeypatch.setenv("DATAMETRONOME_CELERY_BROKER_URL", "amqp://prod:secret@mq:5672//")
    monkeypatch.setenv("DATAMETRONOME_CELERY_RESULT_BACKEND", "redis://prod-redis:6379/1")
    monkeypatch.setenv("DATAMETRONOME_REDIS_URL", "redis://prod-redis:6379/2")
    monkeypatch.setenv("DATAMETRONOME_CELERY_CONCURRENCY", "8")
    s = Settings(secret_key="x" * 32)
    assert s.celery_broker_url == "amqp://prod:secret@mq:5672//"
    assert s.celery_result_backend == "redis://prod-redis:6379/1"
    assert s.redis_url == "redis://prod-redis:6379/2"
    assert s.celery_concurrency == 8


def test_dispatch_mode_default():
    s = Settings(secret_key="x" * 32)
    assert s.dispatch_mode == "inline"


def test_dispatch_mode_celery(monkeypatch):
    monkeypatch.setenv("DATAMETRONOME_DISPATCH_MODE", "celery")
    s = Settings(secret_key="x" * 32)
    assert s.dispatch_mode == "celery"
