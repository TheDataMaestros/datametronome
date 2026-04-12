"""Verify DbtReadonlyPulse satisfies PulseProtocol structurally."""

from metronome_pulse_core.protocol import PulseProtocol
from metronome_pulse_dbt import DbtReadonlyPulse


def test_satisfies_pulse_protocol():
    """DbtReadonlyPulse must satisfy the structural PulseProtocol."""
    connector = DbtReadonlyPulse(mode="local", project_path="/tmp/fake")
    assert isinstance(connector, PulseProtocol)


def test_has_required_methods():
    """Verify all PulseProtocol methods exist on DbtReadonlyPulse."""
    required = [
        "connect",
        "close",
        "query",
        "query_with_params",
        "execute",
        "execute_many",
        "write",
        "list_tables",
        "get_table_info",
        "begin_transaction",
        "commit_transaction",
        "rollback_transaction",
        "__aenter__",
        "__aexit__",
    ]
    connector = DbtReadonlyPulse(mode="local", project_path="/tmp/fake")
    for method in required:
        assert hasattr(connector, method), f"Missing method: {method}"
        assert callable(getattr(connector, method)), f"{method} is not callable"
