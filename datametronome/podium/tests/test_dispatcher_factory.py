"""Tests for dispatcher factory."""
import pytest
from unittest.mock import patch
from datametronome_podium.core.dispatcher_factory import get_dispatcher, reset_dispatcher


@pytest.fixture(autouse=True)
def _reset():
    """Reset singleton before each test."""
    reset_dispatcher()
    yield
    reset_dispatcher()


def test_get_dispatcher_inline():
    with patch("datametronome_podium.core.dispatcher_factory.settings") as mock_settings:
        mock_settings.dispatch_mode = "inline"
        from datametronome_podium.core.check_dispatcher import InlineDispatcher
        dispatcher = get_dispatcher()
        assert isinstance(dispatcher, InlineDispatcher)


def test_get_dispatcher_celery():
    with patch("datametronome_podium.core.dispatcher_factory.settings") as mock_settings:
        mock_settings.dispatch_mode = "celery"
        from datametronome_podium.core.celery_dispatcher import CeleryDispatcher
        dispatcher = get_dispatcher()
        assert isinstance(dispatcher, CeleryDispatcher)


def test_get_dispatcher_singleton():
    with patch("datametronome_podium.core.dispatcher_factory.settings") as mock_settings:
        mock_settings.dispatch_mode = "inline"
        d1 = get_dispatcher()
        d2 = get_dispatcher()
        assert d1 is d2


def test_get_dispatcher_unknown_raises():
    with patch("datametronome_podium.core.dispatcher_factory.settings") as mock_settings:
        mock_settings.dispatch_mode = "unknown"
        with pytest.raises(ValueError, match="Unknown dispatch_mode"):
            get_dispatcher()
