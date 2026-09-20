"""Every supported data source must be handled everywhere that branches on one.

Three times now a source has been added to some of these dispatch points and
not others -- most recently redshift, which had a connector, a dialect and a
connection tester, but fell through `fetch_sample_rows` to
"Preview not implemented for redshift yet", and was missing from every
list_tables branch so it asked for the whole database instead of one schema.

These assert the branch tables directly rather than executing them: building a
real connector needs credentials and a network. Membership is the thing that
keeps drifting.
"""

import inspect

import pytest

from datametronome_podium.core.connector_factory import BUILDERS
from datametronome_podium.core.sql_dialect import DIALECTS
from datametronome_podium.features.staves import service as stave_svc
from datametronome_podium.features.staves.model import SUPPORTED_DATA_SOURCES
from datametronome_podium.services.connection_tester import TESTERS

# dbt reads build artifacts rather than querying a database, so it has no SQL
# dialect and no schema to scope a table listing to.
NON_SQL_SOURCES = {"dbt"}

# S3 tables are declared in connection_config["tables"], not discovered, so the
# connector has no list_tables to call. SQLite has one nameless schema, and
# BigQuery scopes by dataset rather than schema -- both are handled by their
# own arm of list_connector_tables.
NO_TABLE_DISCOVERY = {"s3", "sqlite", "bigquery"}


@pytest.mark.parametrize("source", SUPPORTED_DATA_SOURCES)
def test_every_source_can_be_built(source):
    assert source in BUILDERS


@pytest.mark.parametrize("source", SUPPORTED_DATA_SOURCES)
def test_every_source_can_be_connection_tested(source):
    assert source in TESTERS


@pytest.mark.parametrize(
    "source", [s for s in SUPPORTED_DATA_SOURCES if s not in NON_SQL_SOURCES]
)
def test_every_sql_source_has_a_dialect(source):
    assert source in DIALECTS


@pytest.mark.parametrize("source", SUPPORTED_DATA_SOURCES)
def test_every_source_has_a_preview_branch(source):
    """fetch_sample_rows must not fall through to its ValueError.

    Read from the source text: reaching the branch for real needs a live
    connection, but a missing branch is visible without one.
    """
    body = inspect.getsource(stave_svc.fetch_sample_rows)
    assert f'"{source}"' in body, (
        f"{source} staves exist but fetch_sample_rows has no branch for them, "
        f"so preview and agent sampling both raise"
    )


@pytest.mark.parametrize(
    "source",
    [s for s in SUPPORTED_DATA_SOURCES if s not in NON_SQL_SOURCES | NO_TABLE_DISCOVERY],
)
def test_schema_scoped_sources_are_listed_as_such(source):
    """A relational source not in _SCHEMA_SCOPED lists the whole database."""
    assert source in stave_svc._SCHEMA_SCOPED, (
        f"{source} is relational but list_connector_tables will not pass it a "
        f"schema, so it lists every table in the database"
    )


def test_the_tables_agree_on_which_sources_exist():
    """No entry anywhere for a source that cannot be created."""
    for name, table in [
        ("connector factory", set(BUILDERS)),
        ("connection testers", set(TESTERS)),
        ("SQL dialects", set(DIALECTS)),
    ]:
        orphans = table - set(SUPPORTED_DATA_SOURCES)
        assert not orphans, f"unreachable {name} entries: {sorted(orphans)}"
