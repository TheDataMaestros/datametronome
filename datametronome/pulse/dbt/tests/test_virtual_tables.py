import pytest
from metronome_pulse_dbt.virtual_tables import VirtualTableEngine


@pytest.fixture
def engine():
    e = VirtualTableEngine()
    e.register_table("models", [
        {"name": "stg_customers", "schema": "public", "materialization": "view", "tags": ["staging", "customers"]},
        {"name": "stg_orders", "schema": "public", "materialization": "view", "tags": ["staging"]},
        {"name": "fct_orders", "schema": "public", "materialization": "table", "tags": ["marts", "finance"]},
    ])
    e.register_table("sources", [
        {"name": "customers", "source_name": "raw", "schema": "raw"},
        {"name": "orders", "source_name": "raw", "schema": "raw"},
    ])
    return e


def test_list_tables(engine):
    assert engine.list_tables() == ["models", "sources"]


def test_query_string(engine):
    rows = engine.query("models")
    assert len(rows) == 3
    assert rows[0]["name"] == "stg_customers"


def test_query_string_unknown_table(engine):
    with pytest.raises(ValueError, match="not found"):
        engine.query("nonexistent")


def test_query_sql_string_is_an_unknown_table(engine):
    with pytest.raises(ValueError, match="not found"):
        engine.query("SELECT * FROM models")


def test_query_dict_basic(engine):
    rows = engine.query({"table": "models"})
    assert len(rows) == 3


def test_query_where_equality(engine):
    rows = engine.query({"table": "models", "where": {"materialization": "table"}})
    assert len(rows) == 1
    assert rows[0]["name"] == "fct_orders"


def test_query_where_list_containment(engine):
    rows = engine.query({"table": "models", "where": {"tags": "finance"}})
    assert len(rows) == 1
    assert rows[0]["name"] == "fct_orders"



def test_query_limit(engine):
    rows = engine.query({"table": "models", "limit": 2})
    assert len(rows) == 2




def test_query_combined(engine):
    rows = engine.query({
        "table": "models",
        "where": {"tags": "staging"},
        "limit": 1,
    })
    assert len(rows) == 1
    assert "staging" in rows[0]["tags"]





def test_register_overwrites(engine):
    engine.register_table("models", [{"name": "only_one"}])
    rows = engine.query("models")
    assert len(rows) == 1
    assert rows[0]["name"] == "only_one"
