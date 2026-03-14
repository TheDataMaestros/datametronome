"""Factory for creating the appropriate CheckDispatcher based on config.

Returns a singleton — InlineDispatcher stores job state in instance dicts,
so every request must use the same instance to look up previous jobs.
"""
from datametronome_podium.core.check_dispatcher import CheckDispatcher
from datametronome_podium.core.config import settings

_dispatcher: CheckDispatcher | None = None


def get_dispatcher() -> CheckDispatcher:
    """Get (or create) the singleton CheckDispatcher based on settings.dispatch_mode."""
    global _dispatcher
    if _dispatcher is not None:
        return _dispatcher

    mode = settings.dispatch_mode

    if mode == "inline":
        from datametronome_podium.core.check_dispatcher import InlineDispatcher
        _dispatcher = InlineDispatcher()
    elif mode == "celery":
        from datametronome_podium.core.celery_dispatcher import CeleryDispatcher
        _dispatcher = CeleryDispatcher()
    elif mode == "remote":
        raise NotImplementedError("RemoteDispatcher not yet implemented")
    else:
        raise ValueError(f"Unknown dispatch_mode: {mode!r}")

    return _dispatcher


def reset_dispatcher() -> None:
    """Reset the singleton (for testing)."""
    global _dispatcher
    _dispatcher = None
