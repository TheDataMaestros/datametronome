# datametronome/pulse/core/tests/test_protocol.py
import pytest

from metronome_pulse_core.protocol import PulseProtocol


class TestPulseProtocol:
    def test_protocol_is_runtime_checkable(self):
        from typing import Protocol, runtime_checkable
        assert issubclass(PulseProtocol, Protocol)

    def test_protocol_defines_connect(self):
        assert hasattr(PulseProtocol, "connect")

    def test_protocol_defines_close(self):
        assert hasattr(PulseProtocol, "close")

    def test_protocol_defines_query_with_params(self):
        assert hasattr(PulseProtocol, "query_with_params")

    def test_protocol_defines_execute(self):
        assert hasattr(PulseProtocol, "execute")

    def test_protocol_defines_execute_many(self):
        assert hasattr(PulseProtocol, "execute_many")

    def test_protocol_defines_write(self):
        assert hasattr(PulseProtocol, "write")

    def test_protocol_defines_list_tables(self):
        assert hasattr(PulseProtocol, "list_tables")

    def test_protocol_defines_get_table_info(self):
        assert hasattr(PulseProtocol, "get_table_info")

    def test_protocol_defines_begin_transaction(self):
        assert hasattr(PulseProtocol, "begin_transaction")

    def test_protocol_defines_commit_transaction(self):
        assert hasattr(PulseProtocol, "commit_transaction")

    def test_protocol_defines_rollback_transaction(self):
        assert hasattr(PulseProtocol, "rollback_transaction")

    def test_mock_connector_satisfies_protocol(self):
        class MockPulse:
            async def connect(self) -> None: ...
            async def close(self) -> None: ...
            async def query(self, query_config): ...
            async def query_with_params(self, sql, params=None): ...
            async def execute(self, sql, params=None) -> int: return 0
            async def execute_many(self, sql, params_list) -> None: ...
            async def write(self, data, destination, config=None) -> None: ...
            async def list_tables(self): ...
            async def get_table_info(self, table_name): ...
            async def begin_transaction(self) -> None: ...
            async def commit_transaction(self) -> None: ...
            async def rollback_transaction(self) -> None: ...
            async def __aenter__(self): return self
            async def __aexit__(self, *args): ...

        assert isinstance(MockPulse(), PulseProtocol)
