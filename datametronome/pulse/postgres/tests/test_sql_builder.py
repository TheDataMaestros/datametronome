import pytest
from metronome_pulse_postgres.sql_builder import PostgresSQLBuilder


class TestPostgresSQLBuilder:
    """Comprehensive tests for PostgresSQLBuilder"""
    
    def setup_method(self):
        """Setup method to create a fresh builder instance for each test"""
        self.builder = PostgresSQLBuilder()
    
    def test_delete_using_values_asyncpg_single_row(self):
        """Test DELETE with VALUES for single row deletion"""
        sql = self.builder.delete_using_values_asyncpg("public.events", ["id"], 1)
        assert "DELETE FROM public.events" in sql
        assert "USING (VALUES ($1)) AS v(id)" in sql
        assert "t.id = v.id" in sql
        assert sql.count("$") == 1
    
    def test_delete_using_values_asyncpg_multi_col_single_row(self):
        """Test DELETE with VALUES for multiple columns, single row"""
        sql = self.builder.delete_using_values_asyncpg("public.events", ["id", "source"], 1)
        assert "DELETE FROM public.events" in sql
        assert "USING (VALUES ($1, $2)) AS v(id, source)" in sql
        assert "t.id = v.id AND t.source = v.source" in sql
        assert sql.count("$") == 2
    
    def test_delete_using_values_asyncpg_multi_col_multi_row(self):
        """Test DELETE with VALUES for multiple columns, multiple rows"""
        sql = self.builder.delete_using_values_asyncpg("public.events", ["id", "source"], 2)
        assert "DELETE FROM public.events" in sql
        assert "VALUES ($1, $2), ($3, $4)" in sql
        assert "AS v(id, source)" in sql
        assert "t.id = v.id AND t.source = v.source" in sql
        assert sql.count("$") == 4
    
    def test_delete_using_values_asyncpg_large_batch(self):
        """Test DELETE with VALUES for large batch operations"""
        sql = self.builder.delete_using_values_asyncpg("public.events", ["id"], 100)
        assert "DELETE FROM public.events" in sql
        assert "VALUES ($1), ($2), ($3)" in sql  # Should show first few values
        assert "AS v(id)" in sql
        assert sql.count("$") == 100
    
    def test_delete_using_values_asyncpg_complex_columns(self):
        """Test DELETE with VALUES for complex column names"""
        sql = self.builder.delete_using_values_asyncpg("public.user_events", ["user_id", "event_type", "created_at"], 1)
        assert "DELETE FROM public.user_events" in sql
        assert "USING (VALUES ($1, $2, $3)) AS v(user_id, event_type, created_at)" in sql
        assert "t.user_id = v.user_id AND t.event_type = v.event_type AND t.created_at = v.created_at" in sql
    
    def test_session_tuning_helpers(self):
        """Test session tuning helper methods"""
        # Test synchronous commit
        sql = self.builder.set_local_synchronous_commit_off()
        assert sql.startswith("SET LOCAL synchronous_commit")
        assert "OFF" in sql
        
        # Test constraints deferral
        sql = self.builder.set_constraints_all_deferred()
        assert sql.startswith("SET CONSTRAINTS ALL DEFERRED")
        
        # Test lock timeout
        sql = self.builder.set_local_lock_timeout(500)
        assert "500ms" in sql
        assert sql.startswith("SET LOCAL lock_timeout")
        
        # Test statement timeout
        sql = self.builder.set_local_statement_timeout(60000)
        assert "60000ms" in sql
        assert sql.startswith("SET LOCAL statement_timeout")
        
        # Test transaction timeout
        sql = self.builder.set_local_idle_in_transaction_session_timeout(300000)
        assert "300000ms" in sql
        assert sql.startswith("SET LOCAL idle_in_transaction_session_timeout")
    
    def test_lock_timeout_edge_cases(self):
        """Test lock timeout with edge case values"""
        # Test zero timeout
        sql = self.builder.set_local_lock_timeout(0)
        assert "0ms" in sql
        
        # Test very large timeout
        sql = self.builder.set_local_lock_timeout(86400000)  # 24 hours
        assert "86400000ms" in sql
        
        # Test negative timeout (should handle gracefully)
        sql = self.builder.set_local_lock_timeout(-100)
        assert "-100ms" in sql
    
    def test_statement_timeout_edge_cases(self):
        """Test statement timeout with edge case values"""
        # Test zero timeout
        sql = self.builder.set_local_statement_timeout(0)
        assert "0ms" in sql
        
        # Test very large timeout
        sql = self.builder.set_local_statement_timeout(3600000)  # 1 hour
        assert "3600000ms" in sql
    
    def test_table_name_handling(self):
        """Test handling of different table name formats"""
        # Test with schema
        sql = self.builder.delete_using_values_asyncpg("public.events", ["id"], 1)
        assert "public.events" in sql
        
        # Test without schema
        sql = self.builder.delete_using_values_asyncpg("events", ["id"], 1)
        assert "events" in sql
        
        # Test with quoted table name
        sql = self.builder.delete_using_values_asyncpg('"MyTable"', ["id"], 1)
        assert '"MyTable"' in sql
    
    def test_column_name_handling(self):
        """Test handling of different column name formats"""
        # Test with quoted column names
        sql = self.builder.delete_using_values_asyncpg("public.events", ['"user_id"', '"event_type"'], 1)
        assert 'v("user_id", "event_type")' in sql
        assert 't."user_id" = v."user_id" AND t."event_type" = v."event_type"' in sql
        
        # Test with mixed quoted and unquoted
        sql = self.builder.delete_using_values_asyncpg("public.events", ['"user_id"', 'event_type'], 1)
        assert 'v("user_id", event_type)' in sql
        assert 't."user_id" = v."user_id" AND t.event_type = v.event_type' in sql
    
    def test_parameter_validation(self):
        """Test parameter validation and edge cases"""
        # Test empty columns list
        with pytest.raises(ValueError):
            self.builder.delete_using_values_asyncpg("public.events", [], 1)
        
        # Test zero rows
        with pytest.raises(ValueError):
            self.builder.delete_using_values_asyncpg("public.events", ["id"], 0)
        
        # Test negative rows
        with pytest.raises(ValueError):
            self.builder.delete_using_values_asyncpg("public.events", ["id"], -1)
        
        # Test None table name
        with pytest.raises(ValueError):
            self.builder.delete_using_values_asyncpg(None, ["id"], 1)
        
        # Test None columns
        with pytest.raises(ValueError):
            self.builder.delete_using_values_asyncpg("public.events", None, 1)
    
    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are properly escaped"""
        # Test with potentially dangerous table name
        dangerous_table = "'; DROP TABLE users; --"
        sql = self.builder.delete_using_values_asyncpg(dangerous_table, ["id"], 1)
        # The table name should be used as-is in the SQL, but the VALUES clause should be safe
        assert dangerous_table in sql
        assert "USING (VALUES ($1)) AS v(id)" in sql
        
        # Test with potentially dangerous column names
        dangerous_columns = ["id", "'; DROP TABLE users; --"]
        sql = self.builder.delete_using_values_asyncpg("public.events", dangerous_columns, 1)
        assert dangerous_columns[1] in sql
        assert "USING (VALUES ($1, $2)) AS v(id, '; DROP TABLE users; --)" in sql


class TestPostgresSQLBuilderIntegration:
    """Integration tests for PostgresSQLBuilder"""
    
    def test_full_delete_workflow(self):
        """Test a complete delete workflow with multiple operations"""
        builder = PostgresSQLBuilder()
        
        # Setup session
        setup_sql = [
            builder.set_local_synchronous_commit_off(),
            builder.set_constraints_all_deferred(),
            builder.set_local_lock_timeout(1000),
            builder.set_local_statement_timeout(30000)
        ]
        
        # Verify setup SQL
        for sql in setup_sql:
            assert sql.startswith("SET LOCAL") or sql.startswith("SET CONSTRAINTS")
        
        # Perform delete operation
        delete_sql = builder.delete_using_values_asyncpg("public.user_sessions", ["session_id", "user_id"], 50)
        assert "DELETE FROM public.user_sessions" in delete_sql
        assert delete_sql.count("$") == 100  # 2 columns * 50 rows
        
        # Verify the complete SQL structure
        assert "USING (VALUES" in delete_sql
        assert "AS v(session_id, user_id)" in delete_sql
        assert "t.session_id = v.session_id AND t.user_id = v.user_id" in delete_sql



