"""The connector factory used to drop every config key except host, port,
database, user and password.

That made RDS and Aurora instances with rds.force_ssl=1 unreachable: there was
no way to ask asyncpg for TLS, and the connection failed with a bare
"connection closed" that says nothing about why.
"""

from datametronome_podium.core.connector_factory import _build_postgres_connector


class _FakePulse:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def _patched(monkeypatch):
    import metronome_pulse_postgres

    monkeypatch.setattr(metronome_pulse_postgres, "PostgresPulse", _FakePulse)
    monkeypatch.setattr(metronome_pulse_postgres, "PostgresReadOnlyPulse", _FakePulse)


BASE = {"host": "db.eu-west-1.rds.amazonaws.com", "database": "app", "user": "app"}


def test_factory_forwards_ssl_to_the_connector(monkeypatch):
    _patched(monkeypatch)

    conn = _build_postgres_connector({**BASE, "ssl": "verify-full"}, read_only=True)
    assert conn.kwargs["ssl"] == "verify-full"
    assert conn.kwargs["host"] == BASE["host"]


def test_factory_omits_ssl_when_not_configured(monkeypatch):
    # asyncpg negotiates on its own; passing ssl=None would override that.
    _patched(monkeypatch)

    assert "ssl" not in _build_postgres_connector(BASE, read_only=False).kwargs


def test_empty_ssl_is_treated_as_unset(monkeypatch):
    _patched(monkeypatch)

    conn = _build_postgres_connector({**BASE, "ssl": ""}, read_only=True)
    assert "ssl" not in conn.kwargs
