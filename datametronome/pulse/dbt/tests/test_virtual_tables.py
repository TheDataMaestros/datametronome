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


def test_query_sql_raises(engine):
    with pytest.raises(ValueError, match="SQL queries are not supported"):
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


def test_query_columns(engine):
    rows = engine.query({"table": "models", "columns": ["name", "schema"]})
    assert len(rows) == 3
    for row in rows:
        assert set(row.keys()) == {"name", "schema"}


def test_query_limit(engine):
    rows = engine.query({"table": "models", "limit": 2})
    assert len(rows) == 2


def test_query_order_by(engine):
    rows = engine.query({"table": "models", "order_by": "name"})
    names = [r["name"] for r in rows]
    assert names == sorted(names)


def test_query_order_by_desc(engine):
    rows = engine.query({"table": "models", "order_by": "-name"})
    names = [r["name"] for r in rows]
    assert names == sorted(names, reverse=True)


def test_query_combined(engine):
    # where: staging tags, columns: name only, order_by name desc, limit 1
    rows = engine.query({
        "table": "models",
        "where": {"tags": "staging"},
        "columns": ["name"],
        "order_by": "-name",
        "limit": 1,
    })
    assert len(rows) == 1
    assert rows[0] == {"name": "stg_orders"}


def test_get_table_info(engine):
    info = engine.get_table_info("models")
    # First row has: name (text), schema (text), materialization (text), tags (array)
    col_map = {c["column_name"]: c["column_type"] for c in info}
    assert col_map["name"] == "text"
    assert col_map["schema"] == "text"
    assert col_map["materialization"] == "text"
    assert col_map["tags"] == "array"


def test_get_table_info_empty_table():
    e = VirtualTableEngine()
    e.register_table("empty", [])
    assert e.get_table_info("empty") == []


def test_get_table_info_unknown_table(engine):
    assert engine.get_table_info("nonexistent") == []


def test_register_overwrites(engine):
    engine.register_table("models", [{"name": "only_one"}])
    rows = engine.query("models")
    assert len(rows) == 1
    assert rows[0]["name"] == "only_one"
