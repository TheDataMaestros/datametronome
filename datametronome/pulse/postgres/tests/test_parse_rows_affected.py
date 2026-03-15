"""Unit tests for _parse_rows_affected across asyncpg status formats."""
import pytest
from metronome_pulse_postgres.writeonly_connector import PostgresWriteOnlyPulse


class TestParseRowsAffected:
    @pytest.mark.parametrize("status,expected", [
        ("INSERT 0 1", 1),
        ("INSERT 0 5", 5),
        ("INSERT 0 0", 0),
        ("UPDATE 3", 3),
        ("UPDATE 0", 0),
        ("DELETE 10", 10),
        ("DELETE 0", 0),
        ("SELECT 100", 100),
        ("CREATE TABLE", 0),
        ("DROP TABLE", 0),
        ("ALTER TABLE", 0),
        ("", 0),
    ])
    def test_parse_rows_affected(self, status: str, expected: int):
        assert PostgresWriteOnlyPulse._parse_rows_affected(status) == expected
