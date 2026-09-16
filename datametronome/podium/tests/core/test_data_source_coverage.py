"""Every supported stave type must be wired end to end.

A type can look supported at the edge and be dead everywhere else. That is how
mysql, redis and mongodb survived in the connection tester long after they
stopped being buildable: each layer had its own list, and nothing compared
them. These tests compare them.
"""

import pytest

from datametronome_podium.core.connector_factory import _build_connector
from datametronome_podium.core.sql_dialect import dialect_for
from datametronome_podium.features.staves.model import SUPPORTED_DATA_SOURCES
from datametronome_podium.features.staves.schema import VALID_DATA_SOURCE_TYPES
from datametronome_podium.services.connection_tester import ConnectionTester

# dbt reads build artifacts rather than querying a database, so it has a
# connector and a tester but no SQL dialect.
NON_SQL_SOURCES = {"dbt"}


def test_the_api_accepts_what_the_model_supports():
    # postgresql is an accepted alias on the model but not offered at the API.
    assert set(VALID_DATA_SOURCE_TYPES) <= set(SUPPORTED_DATA_SOURCES)


@pytest.mark.parametrize("source", SUPPORTED_DATA_SOURCES)
def test_every_supported_source_can_be_built(source):
    # A missing branch raises ValueError. A missing package raises ImportError
    # or KeyError for absent config, which both mean the branch exists.
    try:
        _build_connector(source, {}, read_only=True)
    except ValueError as e:
        if "Unsupported data source type" in str(e):
            raise AssertionError(
                f"connector_factory has no branch for {source}"
            ) from e
    except (KeyError, ImportError, RuntimeError):
        pass


@pytest.mark.parametrize("source", SUPPORTED_DATA_SOURCES)
def test_every_supported_source_has_a_connection_tester(source):
    assert source in ConnectionTester._TESTERS, (
        f"{source} staves can be created but their connection cannot be tested"
    )


@pytest.mark.parametrize(
    "source", [s for s in SUPPORTED_DATA_SOURCES if s not in NON_SQL_SOURCES]
)
def test_every_sql_source_has_a_dialect(source):
    assert dialect_for(source) is not None, (
        f"{source!r} staves can be created but every check against one would "
        "return unsupported_data_source"
    )


def test_the_tester_has_no_entry_for_a_source_that_cannot_be_created():
    orphans = set(ConnectionTester._TESTERS) - set(SUPPORTED_DATA_SOURCES)
    assert not orphans, f"unreachable connection testers: {sorted(orphans)}"
