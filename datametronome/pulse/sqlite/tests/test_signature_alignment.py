import pytest
import inspect
from metronome_pulse_sqlite import SQLitePulse, SQLiteWriteonlyPulse, SQLiteReadonlyPulse


class TestExecuteSignature:
    def test_execute_return_annotation_is_int(self):
        """execute() should return int (rows affected), not bool."""
        sig = inspect.signature(SQLitePulse.execute)
        assert sig.return_annotation is int

    def test_writeonly_execute_return_annotation_is_int(self):
        sig = inspect.signature(SQLiteWriteonlyPulse.execute)
        assert sig.return_annotation is int


class TestQueryWithParamsSignature:
    def test_params_default_is_none(self):
        """query_with_params(params) should default to None."""
        sig = inspect.signature(SQLitePulse.query_with_params)
        assert sig.parameters["params"].default is None

    def test_readonly_params_default_is_none(self):
        sig = inspect.signature(SQLiteReadonlyPulse.query_with_params)
        assert sig.parameters["params"].default is None


class TestExecuteMany:
    def test_execute_many_exists_on_pulse(self):
        assert hasattr(SQLitePulse, "execute_many")

    def test_execute_many_exists_on_writeonly(self):
        assert hasattr(SQLiteWriteonlyPulse, "execute_many")


class TestTransactionMethods:
    def test_begin_transaction_exists_on_writeonly(self):
        assert hasattr(SQLiteWriteonlyPulse, "begin_transaction")

    def test_commit_transaction_exists_on_writeonly(self):
        assert hasattr(SQLiteWriteonlyPulse, "commit_transaction")

    def test_rollback_transaction_exists_on_writeonly(self):
        assert hasattr(SQLiteWriteonlyPulse, "rollback_transaction")

    def test_begin_transaction_exists_on_pulse(self):
        assert hasattr(SQLitePulse, "begin_transaction")

    def test_commit_transaction_exists_on_pulse(self):
        assert hasattr(SQLitePulse, "commit_transaction")

    def test_rollback_transaction_exists_on_pulse(self):
        assert hasattr(SQLitePulse, "rollback_transaction")
