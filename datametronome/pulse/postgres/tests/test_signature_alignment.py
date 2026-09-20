import inspect
from metronome_pulse_postgres import PostgresPulse, PostgresReadOnlyPulse


class TestExecuteSignature:
    def test_execute_accepts_params_list(self):
        """execute() should accept (sql, params=None), not (*args, **kwargs)."""
        sig = inspect.signature(PostgresPulse.execute)
        params = list(sig.parameters.keys())
        assert params == ["self", "sql", "params"], (
            f"Expected (self, sql, params), got {params}"
        )

    def test_execute_params_default_is_none(self):
        sig = inspect.signature(PostgresPulse.execute)
        assert sig.parameters["params"].default is None

    def test_execute_return_annotation_is_int(self):
        sig = inspect.signature(PostgresPulse.execute)
        assert sig.return_annotation is int

    def test_accepts_params_list(self):
        sig = inspect.signature(PostgresPulse.query_with_params)
        params = list(sig.parameters.keys())
        assert params == ["self", "sql", "params"]

    def test_params_default_is_none(self):
        sig = inspect.signature(PostgresPulse.query_with_params)
        assert sig.parameters["params"].default is None

    def test_readonly_accepts_params_list(self):
        sig = inspect.signature(PostgresReadOnlyPulse.query_with_params)
        params = list(sig.parameters.keys())
        assert params == ["self", "sql", "params"]

    def test_readonly_params_default_is_none(self):
        sig = inspect.signature(PostgresReadOnlyPulse.query_with_params)
        assert sig.parameters["params"].default is None


class TestExecuteManySignature:
    def test_execute_many_param_name(self):
        sig = inspect.signature(PostgresPulse.execute_many)
        params = list(sig.parameters.keys())
        assert params == ["self", "sql", "params_list"]

    def test_begin_transaction_exists(self):
        assert hasattr(PostgresPulse, "begin_transaction")
        sig = inspect.signature(PostgresPulse.begin_transaction)
        assert sig.return_annotation is None

    def test_commit_transaction_exists(self):
        assert hasattr(PostgresPulse, "commit_transaction")
        sig = inspect.signature(PostgresPulse.commit_transaction)
        assert sig.return_annotation is None

    def test_rollback_transaction_exists(self):
        assert hasattr(PostgresPulse, "rollback_transaction")
        sig = inspect.signature(PostgresPulse.rollback_transaction)
        assert sig.return_annotation is None
