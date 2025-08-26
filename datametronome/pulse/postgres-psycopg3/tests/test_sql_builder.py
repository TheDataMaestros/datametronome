import pytest
from datametronome.pulse.postgres_psycopg3.metronome_pulse_postgres_psycopg3.sql_builder import (
    PostgresPsycopgSQLBuilder,
)


class TestPostgresPsycopgSQLBuilder:
    """Comprehensive tests for PostgresPsycopgSQLBuilder"""
    
    def setup_method(self):
        """Setup method to create a fresh builder instance for each test"""
        self.builder = PostgresPsycopgSQLBuilder()
    
    def test_delete_using_values_psycopg_build_single_row(self):
        """Test DELETE with VALUES for single row deletion using psycopg3 style"""
        sql = self.builder.delete_using_values("public.tbl", ["id"], 1)
        assert "DELETE FROM public.tbl" in sql
        assert "USING (VALUES (%s)) AS v(id)" in sql
        assert "t.id = v.id" in sql
        assert sql.count("%s") == 1
    
    def test_delete_using_values_psycopg_build_multi_col_single_row(self):
        """Test DELETE with VALUES for multiple columns, single row"""
        sql = self.builder.delete_using_values("public.tbl", ["id", "k"], 1)
        assert "DELETE FROM public.tbl" in sql
        assert "USING (VALUES (%s, %s)) AS v(id, k)" in sql
        assert "t.id = v.id AND t.k = v.k" in sql
        assert sql.count("%s") == 2
    
    def test_delete_using_values_psycopg_build_multi_col_multi_row(self):
        """Test DELETE with VALUES for multiple columns, multiple rows"""
        sql = self.builder.delete_using_values("public.tbl", ["id", "k"], 3)
        assert "DELETE FROM public.tbl" in sql
        assert "VALUES (%s, %s), (%s, %s), (%s, %s)" in sql
        assert "AS v(id, k)" in sql
        assert "t.id = v.id AND t.k = v.k" in sql
        assert sql.count("%s") == 6
    
    def test_delete_using_values_psycopg_build_large_batch(self):
        """Test DELETE with VALUES for large batch operations"""
        sql = self.builder.delete_using_values("public.events", ["id"], 100)
        assert "DELETE FROM public.events" in sql
        assert "VALUES (%s), (%s), (%s)" in sql  # Should show first few values
        assert "AS v(id)" in sql
        assert sql.count("%s") == 100
    
    def test_delete_using_values_psycopg_build_complex_columns(self):
        """Test DELETE with VALUES for complex column names"""
        sql = self.builder.delete_using_values("public.user_events", ["user_id", "event_type", "created_at"], 1)
        assert "DELETE FROM public.user_events" in sql
        assert "USING (VALUES (%s, %s, %s)) AS v(user_id, event_type, created_at)" in sql
        assert "t.user_id = v.user_id AND t.event_type = v.event_type AND t.created_at = v.created_at" in sql
    
    def test_table_name_handling(self):
        """Test handling of different table name formats"""
        # Test with schema
        sql = self.builder.delete_using_values("public.events", ["id"], 1)
        assert "public.events" in sql
        
        # Test without schema
        sql = self.builder.delete_using_values("events", ["id"], 1)
        assert "events" in sql
        
        # Test with quoted table name
        sql = self.builder.delete_using_values('"MyTable"', ["id"], 1)
        assert '"MyTable"' in sql
        
        # Test with complex schema names
        sql = self.builder.delete_using_values("my_schema.my_table", ["id"], 1)
        assert "my_schema.my_table" in sql
    
    def test_column_name_handling(self):
        """Test handling of different column name formats"""
        # Test with quoted column names
        sql = self.builder.delete_using_values("public.events", ['"user_id"', '"event_type"'], 1)
        assert 'v("user_id", "event_type")' in sql
        assert 't."user_id" = v."user_id" AND t."event_type" = v."event_type"' in sql
        
        # Test with mixed quoted and unquoted
        sql = self.builder.delete_using_values("public.events", ['"user_id"', 'event_type'], 1)
        assert 'v("user_id", event_type)' in sql
        assert 't."user_id" = v."user_id" AND t.event_type = v.event_type' in sql
        
        # Test with underscore columns
        sql = self.builder.delete_using_values("public.events", ["user_id", "event_type"], 1)
        assert "v(user_id, event_type)" in sql
        assert "t.user_id = v.user_id AND t.event_type = v.event_type" in sql
    
    def test_parameter_validation(self):
        """Test parameter validation and edge cases"""
        # Test empty columns list
        with pytest.raises(ValueError):
            self.builder.delete_using_values("public.events", [], 1)
        
        # Test zero rows
        with pytest.raises(ValueError):
            self.builder.delete_using_values("public.events", ["id"], 0)
        
        # Test negative rows
        with pytest.raises(ValueError):
            self.builder.delete_using_values("public.events", ["id"], -1)
        
        # Test None table name
        with pytest.raises(ValueError):
            self.builder.delete_using_values(None, ["id"], 1)
        
        # Test None columns
        with pytest.raises(ValueError):
            self.builder.delete_using_values("public.events", None, 1)
    
    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are properly handled"""
        # Test with potentially dangerous table name
        dangerous_table = "'; DROP TABLE users; --"
        sql = self.builder.delete_using_values(dangerous_table, ["id"], 1)
        # The table name should be used as-is in the SQL, but the VALUES clause should be safe
        assert dangerous_table in sql
        assert "USING (VALUES (%s)) AS v(id)" in sql
        
        # Test with potentially dangerous column names
        dangerous_columns = ["id", "'; DROP TABLE users; --"]
        sql = self.builder.delete_using_values("public.events", dangerous_columns, 1)
        assert dangerous_columns[1] in sql
        assert "USING (VALUES (%s, %s)) AS v(id, '; DROP TABLE users; --)" in sql
    
    def test_different_placeholder_styles(self):
        """Test that psycopg3 style placeholders are used consistently"""
        # All placeholders should be %s style
        sql = self.builder.delete_using_values("public.events", ["id", "name", "value"], 5)
        assert sql.count("%s") == 15  # 3 columns * 5 rows
        assert "$" not in sql  # No asyncpg style placeholders
        
        # Verify placeholder pattern
        assert "VALUES (%s, %s, %s), (%s, %s, %s), (%s, %s, %s), (%s, %s, %s), (%s, %s, %s)" in sql
    
    def test_edge_case_row_counts(self):
        """Test edge case row counts"""
        # Test single row
        sql = self.builder.delete_using_values("public.events", ["id"], 1)
        assert sql.count("%s") == 1
        
        # Test two rows
        sql = self.builder.delete_using_values("public.events", ["id"], 2)
        assert sql.count("%s") == 2
        
        # Test large number
        sql = self.builder.delete_using_values("public.events", ["id"], 1000)
        assert sql.count("%s") == 1000
    
    def test_column_count_edge_cases(self):
        """Test edge cases for column counts"""
        # Test single column
        sql = self.builder.delete_using_values("public.events", ["id"], 1)
        assert "v(id)" in sql
        
        # Test many columns
        many_columns = ["col1", "col2", "col3", "col4", "col5", "col6", "col7", "col8", "col9", "col10"]
        sql = self.builder.delete_using_values("public.events", many_columns, 1)
        assert "v(col1, col2, col3, col4, col5, col6, col7, col8, col9, col10)" in sql
        assert sql.count("%s") == 10
    
    def test_sql_structure_validation(self):
        """Test that generated SQL has correct structure"""
        sql = self.builder.delete_using_values("public.events", ["id", "name"], 3)
        
        # Check basic structure
        assert sql.startswith("DELETE FROM")
        assert "USING (VALUES" in sql
        assert "AS v(" in sql
        assert "WHERE" in sql
        
        # Check that table alias is used consistently
        assert "t.id = v.id AND t.name = v.name" in sql
        
        # Check that VALUES clause is properly formatted
        assert "VALUES (%s, %s), (%s, %s), (%s, %s)" in sql


class TestPostgresPsycopgSQLBuilderIntegration:
    """Integration tests for PostgresPsycopgSQLBuilder"""
    
    def test_full_delete_workflow(self):
        """Test a complete delete workflow with multiple operations"""
        builder = PostgresPsycopgSQLBuilder()
        
        # Perform delete operation with multiple columns and rows
        delete_sql = builder.delete_using_values("public.user_sessions", ["session_id", "user_id", "created_at"], 50)
        
        # Verify the complete SQL structure
        assert "DELETE FROM public.user_sessions" in delete_sql
        assert delete_sql.count("%s") == 150  # 3 columns * 50 rows
        assert "USING (VALUES" in delete_sql
        assert "AS v(session_id, user_id, created_at)" in delete_sql
        assert "t.session_id = v.session_id AND t.user_id = v.user_id AND t.created_at = v.created_at" in delete_sql
    
    def test_consistency_across_different_operations(self):
        """Test that the builder produces consistent SQL across different operations"""
        builder = PostgresPsycopgSQLBuilder()
        
        # Test different table/column combinations
        operations = [
            ("public.users", ["id"], 10),
            ("public.orders", ["order_id", "user_id"], 25),
            ("public.products", ["product_id", "category_id", "price"], 100),
        ]
        
        for table, columns, rows in operations:
            sql = builder.delete_using_values(table, columns, rows)
            assert f"DELETE FROM {table}" in sql
            assert f"AS v({', '.join(columns)})" in sql
            assert sql.count("%s") == len(columns) * rows
            
            # Verify WHERE clause structure
            where_conditions = [f"t.{col} = v.{col}" for col in columns]
            expected_where = " AND ".join(where_conditions)
            assert expected_where in sql



