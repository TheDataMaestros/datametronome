"""Tests for Celery app configuration."""
import pytest
from unittest.mock import patch, MagicMock


def test_celery_app_importable():
    from datametronome_podium.core.celery_app import celery_app
    assert celery_app is not None


def test_celery_app_name():
    from datametronome_podium.core.celery_app import celery_app
    assert celery_app.main == "datametronome"


def test_celery_app_has_queue_config():
    from datametronome_podium.core.celery_app import celery_app
    routes = celery_app.conf.task_routes
    assert routes is not None


def test_celery_app_serializer_is_json():
    from datametronome_podium.core.celery_app import celery_app
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]


def test_celery_app_retry_defaults():
    from datametronome_podium.core.celery_app import celery_app
    assert celery_app.conf.task_default_retry_delay == 10
    assert celery_app.conf.task_max_retries == 3


def test_celery_app_queue_definitions():
    from datametronome_podium.core.celery_app import QUEUE_HIGH, QUEUE_DEFAULT, QUEUE_BULK, QUEUE_DLQ
    assert QUEUE_HIGH == "checks.high"
    assert QUEUE_DEFAULT == "checks.default"
    assert QUEUE_BULK == "checks.bulk"
    assert QUEUE_DLQ == "checks.dlq"
