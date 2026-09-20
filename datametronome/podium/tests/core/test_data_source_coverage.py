"""Every supported stave type must be wired end to end.

A type can look supported at the edge and be dead everywhere else. That is how
mysql, redis and mongodb survived in the connection tester long after they
stopped being buildable: each layer had its own list, and nothing compared
them. These tests compare them.
"""

import pytest

from datametronome_podium.core.connector_factory import BUILDERS, _build_connector
from datametronome_podium.core.sql_dialect import dialect_for
from datametronome_podium.features.staves.model import SUPPORTED_DATA_SOURCES
from datametronome_podium.features.staves.schema import VALID_DATA_SOURCE_TYPES
from datametronome_podium.services.connection_tester import TESTERS

# dbt reads build artifacts rather than querying a database, so it has a
# connector and a tester but no SQL dialect.
NON_SQL_SOURCES = {"dbt"}


def test_the_api_accepts_what_the_model_supports():
    # postgresql is an accepted alias on the model but not offered at the API.
    assert set(VALID_DATA_SOURCE_TYPES) <= set(SUPPORTED_DATA_SOURCES)


def test_the_types_endpoint_advertises_every_type_it_accepts():
    """GET /staves/types must not keep its own copy of the list.

    It did, and the copy drifted: it still returned postgres, sqlite, bigquery
    and dbt after redshift and s3 shipped. Creation worked, because the schema
    gates that, so nothing failed. A client building a picker from the endpoint
    simply could not offer the new types.
    """
    from datametronome_podium.features.staves import router

    assert router.VALID_DATA_SOURCE_TYPES is VALID_DATA_SOURCE_TYPES


@pytest.mark.parametrize("source", SUPPORTED_DATA_SOURCES)
def test_every_supported_source_can_be_built(source):
    # Membership, not construction. Building a BigQueryPulse reaches out to the
    # GCP metadata server for credential discovery, which took 33 seconds and
    # blew the suite timeout. Whether the factory knows the type is the
    # question here; the per-connector tests cover config mapping.
    assert source in BUILDERS, f"connector_factory has no builder for {source}"


def test_an_unknown_source_is_rejected():
    with pytest.raises(ValueError, match="Unsupported data source type"):
        _build_connector("cassandra", {})


@pytest.mark.parametrize("source", SUPPORTED_DATA_SOURCES)
def test_every_supported_source_has_a_connection_tester(source):
    assert source in TESTERS, (
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
    orphans = set(TESTERS) - set(SUPPORTED_DATA_SOURCES)
    assert not orphans, f"unreachable connection testers: {sorted(orphans)}"
