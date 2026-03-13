import pytest
from metronome_pulse_core.protocol import PulseProtocol


class TestProtocolCompliance:
    def test_postgres_pulse_satisfies_protocol(self):
        from metronome_pulse_postgres import PostgresPulse
        pulse = PostgresPulse.__new__(PostgresPulse)
        assert isinstance(pulse, PulseProtocol)

    def test_sqlite_pulse_satisfies_protocol(self):
        from metronome_pulse_sqlite import SQLitePulse
        pulse = SQLitePulse.__new__(SQLitePulse)
        assert isinstance(pulse, PulseProtocol)

    def test_postgres_writeonly_satisfies_protocol(self):
        from metronome_pulse_postgres import PostgresWriteOnlyPulse
        pulse = PostgresWriteOnlyPulse.__new__(PostgresWriteOnlyPulse)
        assert isinstance(pulse, PulseProtocol)

    def test_sqlite_writeonly_satisfies_protocol(self):
        from metronome_pulse_sqlite import SQLiteWriteonlyPulse
        pulse = SQLiteWriteonlyPulse.__new__(SQLiteWriteonlyPulse)
        assert isinstance(pulse, PulseProtocol)
