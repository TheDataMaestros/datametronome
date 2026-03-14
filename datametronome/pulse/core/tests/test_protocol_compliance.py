from metronome_pulse_core.protocol import PulseProtocol


class TestProtocolCompliance:
    """Full-featured connectors must satisfy PulseProtocol.

    Write-only and read-only connectors are excluded — they intentionally
    lack read or write methods respectively. Only the combined connectors
    (PostgresPulse, SQLitePulse) implement the full interface.
    """

    def test_postgres_pulse_satisfies_protocol(self):
        from metronome_pulse_postgres import PostgresPulse
        pulse = PostgresPulse.__new__(PostgresPulse)
        assert isinstance(pulse, PulseProtocol)

    def test_sqlite_pulse_satisfies_protocol(self):
        from metronome_pulse_sqlite import SQLitePulse
        pulse = SQLitePulse.__new__(SQLitePulse)
        assert isinstance(pulse, PulseProtocol)
