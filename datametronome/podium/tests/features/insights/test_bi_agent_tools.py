# All async tests require @pytest.mark.asyncio (asyncio mode: STRICT)
import pytest
from datametronome_podium.services.agents.business_intelligence import (
    _apply_schema, _execute_sql,
)

def test_apply_schema_simple():
    sql = 'SELECT * FROM {schema}."orders"'
    result = _apply_schema(sql, '"myschema".')
    assert result == 'SELECT * FROM "myschema"."orders"'

def test_apply_schema_with_placeholder():
    sql = "SELECT * FROM {schema}.products WHERE name = '{entity_name}'"
    result = _apply_schema(sql, '"olist".', entity_name="Widget Pro")
    assert '"olist"' in result
    assert "Widget Pro" in result

@pytest.mark.asyncio
async def test_execute_sql_returns_dicts():
    class MockConnector:
        async def query(self, q):
            return [{"value": 42}]
    rows = await _execute_sql(MockConnector(), "SELECT 1")
    assert rows == [{"value": 42}]

@pytest.mark.asyncio
async def test_execute_sql_handles_failure():
    class FailConnector:
        async def query(self, q):
            raise RuntimeError("connection refused")
    rows = await _execute_sql(FailConnector(), "SELECT 1")
    assert rows == []
