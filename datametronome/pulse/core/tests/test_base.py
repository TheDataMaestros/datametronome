import pytest
from metronome_pulse_core.base import BaseConnector
from metronome_pulse_core.interfaces import (
    Pulse,
    Readable,
    Writable,
    ReadOnlyConnector,
    WriteOnlyConnector,
    ReadWriteConnector,
)


class TestBaseConnector:
    """Comprehensive tests for BaseConnector"""
    
    def test_base_connector_instantiation(self):
        """Test that BaseConnector can be instantiated"""
        # BaseConnector is abstract, so we need to create a concrete implementation
        class ConcreteConnector(BaseConnector):
            def connect(self):
                return True
    
            def close(self):
                return True
    
            def disconnect(self):
                return True
    
            def is_connected(self):
                return True
            
            def execute_query(self, query: str, params: dict = None):
                return [{"result": "data"}]
            
            def get_freshness(self):
                return "unknown"
            
            def get_row_count(self):
                return 0
            
            def get_schema(self):
                return {}
            
            def get_table_info(self, table_name: str):
                return []
            
            def test_connection(self):
                return True
        
        from metronome_pulse_core.base import ConnectionConfig
        config = ConnectionConfig(host="localhost", port=5432, database="test")
        connector = ConcreteConnector(config)
        assert connector is not None
        assert isinstance(connector, BaseConnector)
    
    def test_base_connector_abstract_methods(self):
        """Test that BaseConnector requires implementation of abstract methods"""
        with pytest.raises(TypeError):
            BaseConnector()
    
    def test_base_connector_inheritance(self):
        """Test that concrete connectors properly inherit from BaseConnector"""
        class TestConnector(BaseConnector):
            def connect(self):
                return "connected"
            
            def close(self):
                return "closed"
            
            def disconnect(self):
                return "disconnected"
            
            def is_connected(self):
                return True
            
            def execute_query(self, query: str, params: dict = None):
                return [{"result": "data"}]
            
            def get_freshness(self):
                return "unknown"
            
            def get_row_count(self):
                return 0
            
            def get_schema(self):
                return {}
            
            def get_table_info(self, table_name: str):
                return []
            
            def test_connection(self):
                return True
        
        from metronome_pulse_core.base import ConnectionConfig
        config = ConnectionConfig(host="localhost", port=5432, database="test")
        connector = TestConnector(config)
        assert isinstance(connector, BaseConnector)
        assert connector.connect() == "connected"
        assert connector.disconnect() == "disconnected"
        assert connector.is_connected() is True


class TestReadable:
    """Comprehensive tests for Readable interface"""
    
    def test_readable_connector_instantiation(self):
        """Test that Readable can be instantiated"""
        class ConcreteReadable(Pulse, Readable):
            def connect(self):
                return True
    
            def close(self):
                return True
    
            def disconnect(self):
                return True
    
            def is_connected(self):
                return True
    
            def query(self, query_config):
                return [{"result": "data"}]
    
            def execute_query(self, query: str, params: dict = None):
                return [{"result": "data"}]
    
            def fetch_one(self, query: str, params: dict = None):
                return [{"result": "all"}]
    
            def fetch_all(self, query: str, params: dict = None):
                return [{"result": "all"}]
        
        connector = ConcreteReadable()
        assert connector is not None
        assert isinstance(connector, Readable)
        assert isinstance(connector, Pulse)
    
    def test_readonly_connector_abstract_methods(self):
        """Test that ReadOnlyConnector requires implementation of abstract methods"""
        with pytest.raises(TypeError):
            ReadOnlyConnector()
    
    def test_readonly_connector_methods(self):
        """Test that ReadOnlyConnector has all required methods"""
        class TestReadOnlyConnector(ReadOnlyConnector):
            def connect(self):
                return True
            
            def close(self):
                return True
            
            def disconnect(self):
                return True
            
            def is_connected(self):
                return True
            
            def query(self, query_config):
                return [{"result": "data"}]
            
            def execute_query(self, query: str, params: dict = None):
                return [{"result": "data"}]
            
            def fetch_one(self, query: str, params: dict = None):
                return {"result": "single"}
            
            def fetch_all(self, query: str, params: dict = None):
                return [{"result": "all"}]
        
        connector = TestReadOnlyConnector()
        
        # Test all required methods exist and work
        assert connector.execute_query("SELECT * FROM test") == [{"result": "data"}]
        assert connector.fetch_one("SELECT * FROM test") == {"result": "single"}
        assert connector.fetch_all("SELECT * FROM test") == [{"result": "all"}]
    
    def test_readonly_connector_query_parameters(self):
        """Test that ReadOnlyConnector handles query parameters correctly"""
        class TestReadOnlyConnector(ReadOnlyConnector):
            def connect(self):
                return True
            
            def disconnect(self):
                return True
            
            def is_connected(self):
                return True
            
            def execute_query(self, query: str, params: dict = None):
                return {"query": query, "params": params}
            
            def fetch_one(self, query: str, params: dict = None):
                return {"query": query, "params": params}
            
            def fetch_all(self, query: str, params: dict = None):
                return [{"query": query, "params": params}]
        
        connector = TestReadOnlyConnector()
        
        # Test with parameters
        params = {"id": 1, "name": "test"}
        result = connector.execute_query("SELECT * FROM test WHERE id = :id", params)
        assert result["params"] == params
        
        # Test without parameters
        result = connector.execute_query("SELECT * FROM test")
        assert result["params"] is None


class TestWriteOnlyConnector:
    """Comprehensive tests for WriteOnlyConnector interface"""
    
    def test_writeonly_connector_instantiation(self):
        """Test that WriteOnlyConnector can be instantiated"""
        class ConcreteWriteOnlyConnector(WriteOnlyConnector):
            def connect(self):
                return True
            
            def disconnect(self):
                return True
            
            def is_connected(self):
                return True
            
            def execute_write(self, query: str, params: dict = None):
                return {"affected_rows": 1}
            
            def execute_batch(self, queries: list[str], params: list[dict] = None):
                return {"affected_rows": [1, 2, 3]}
            
            def begin_transaction(self):
                return True
            
            def commit_transaction(self):
                return True
            
            def rollback_transaction(self):
                return True
        
        connector = ConcreteWriteOnlyConnector()
        assert connector is not None
        assert isinstance(connector, WriteOnlyConnector)
        assert isinstance(connector, BaseConnector)
    
    def test_writeonly_connector_abstract_methods(self):
        """Test that WriteOnlyConnector requires implementation of abstract methods"""
        with pytest.raises(TypeError):
            WriteOnlyConnector()
    
    def test_writeonly_connector_methods(self):
        """Test that WriteOnlyConnector has all required methods"""
        class TestWriteOnlyConnector(WriteOnlyConnector):
            def connect(self):
                return True
            
            def disconnect(self):
                return True
            
            def is_connected(self):
                return True
            
            def execute_write(self, query: str, params: dict = None):
                return {"affected_rows": 1}
            
            def execute_batch(self, queries: list[str], params: list[dict] = None):
                return {"affected_rows": [1, 2, 3]}
            
            def begin_transaction(self):
                return True
            
            def commit_transaction(self):
                return True
            
            def rollback_transaction(self):
                return True
        
        connector = TestWriteOnlyConnector()
        
        # Test all required methods exist and work
        assert connector.execute_write("INSERT INTO test VALUES (:id)", {"id": 1}) == {"affected_rows": 1}
        assert connector.execute_batch(["INSERT INTO test VALUES (1)", "INSERT INTO test VALUES (2)"]) == {"affected_rows": [1, 2, 3]}
        assert connector.begin_transaction() is True
        assert connector.commit_transaction() is True
        assert connector.rollback_transaction() is True
    
    def test_writeonly_connector_transaction_flow(self):
        """Test that WriteOnlyConnector handles transaction flow correctly"""
        class TestWriteOnlyConnector(WriteOnlyConnector):
            def __init__(self):
                self.transaction_state = "none"
            
            def connect(self):
                return True
            
            def disconnect(self):
                return True
            
            def is_connected(self):
                return True
            
            def execute_write(self, query: str, params: dict = None):
                return {"affected_rows": 1}
            
            def execute_batch(self, queries: list[str], params: list[dict] = None):
                return {"affected_rows": [1, 2, 3]}
            
            def begin_transaction(self):
                self.transaction_state = "active"
                return True
            
            def commit_transaction(self):
                if self.transaction_state == "active":
                    self.transaction_state = "committed"
                    return True
                return False
            
            def rollback_transaction(self):
                if self.transaction_state == "active":
                    self.transaction_state = "rolled_back"
                    return True
                return False
        
        connector = TestWriteOnlyConnector()
        
        # Test transaction flow
        assert connector.transaction_state == "none"
        assert connector.begin_transaction() is True
        assert connector.transaction_state == "active"
        assert connector.commit_transaction() is True
        assert connector.transaction_state == "committed"
        
        # Test rollback
        connector.transaction_state = "active"
        assert connector.rollback_transaction() is True
        assert connector.transaction_state == "rolled_back"


class TestReadWriteConnector:
    """Comprehensive tests for ReadWriteConnector interface"""
    
    def test_readwrite_connector_instantiation(self):
        """Test that ReadWriteConnector can be instantiated"""
        class ConcreteReadWriteConnector(ReadWriteConnector):
            def connect(self):
                return True
            
            def disconnect(self):
                return True
            
            def is_connected(self):
                return True
            
            def execute_query(self, query: str, params: dict = None):
                return [{"result": "data"}]
            
            def fetch_one(self, query: str, params: dict = None):
                return {"result": "single"}
            
            def fetch_all(self, query: str, params: dict = None):
                return [{"result": "all"}]
            
            def execute_write(self, query: str, params: dict = None):
                return {"affected_rows": 1}
            
            def execute_batch(self, queries: list[str], params: list[dict] = None):
                return {"affected_rows": [1, 2, 3]}
            
            def begin_transaction(self):
                return True
            
            def commit_transaction(self):
                return True
            
            def rollback_transaction(self):
                return True
        
        connector = ConcreteReadWriteConnector()
        assert connector is not None
        assert isinstance(connector, ReadWriteConnector)
        assert isinstance(connector, ReadOnlyConnector)
        assert isinstance(connector, WriteOnlyConnector)
        assert isinstance(connector, BaseConnector)
    
    def test_readwrite_connector_abstract_methods(self):
        """Test that ReadWriteConnector requires implementation of abstract methods"""
        with pytest.raises(TypeError):
            ReadWriteConnector()
    
    def test_readwrite_connector_full_functionality(self):
        """Test that ReadWriteConnector provides full read/write functionality"""
        class TestReadWriteConnector(ReadWriteConnector):
            def __init__(self):
                self.transaction_state = "none"
                self.data = []
            
            def connect(self):
                return True
            
            def disconnect(self):
                return True
            
            def is_connected(self):
                return True
            
            def execute_query(self, query: str, params: dict = None):
                return self.data
            
            def fetch_one(self, query: str, params: dict = None):
                return self.data[0] if self.data else None
            
            def fetch_all(self, query: str, params: dict = None):
                return self.data
            
            def execute_write(self, query: str, params: dict = None):
                if "INSERT" in query.upper():
                    self.data.append(params or {})
                    return {"affected_rows": 1}
                elif "DELETE" in query.upper():
                    if self.data:
                        self.data.pop()
                        return {"affected_rows": 1}
                    return {"affected_rows": 0}
                return {"affected_rows": 0}
            
            def execute_batch(self, queries: list[str], params: list[dict] = None):
                affected_rows = []
                for i, query in enumerate(query):
                    param = params[i] if params and i < len(params) else None
                    result = self.execute_write(query, param)
                    affected_rows.append(result["affected_rows"])
                return {"affected_rows": affected_rows}
            
            def begin_transaction(self):
                self.transaction_state = "active"
                return True
            
            def commit_transaction(self):
                if self.transaction_state == "active":
                    self.transaction_state = "committed"
                    return True
                return False
            
            def rollback_transaction(self):
                if self.transaction_state == "active":
                    self.transaction_state = "rolled_back"
                    return True
                return False
        
        connector = TestReadWriteConnector()
        
        # Test read operations
        assert connector.fetch_all("SELECT * FROM test") == []
        assert connector.fetch_one("SELECT * FROM test") is None
        
        # Test write operations
        assert connector.execute_write("INSERT INTO test VALUES (:id)", {"id": 1}) == {"affected_rows": 1}
        assert len(connector.data) == 1
        
        # Test read after write
        assert connector.fetch_all("SELECT * FROM test") == [{"id": 1}]
        assert connector.fetch_one("SELECT * FROM test") == {"id": 1}
        
        # Test transaction operations
        assert connector.begin_transaction() is True
        assert connector.transaction_state == "active"
        assert connector.commit_transaction() is True
        assert connector.transaction_state == "committed"
        
        # Test rollback
        connector.transaction_state = "active"
        assert connector.rollback_transaction() is True
        assert connector.transaction_state == "rolled_back"


class TestConnectorIntegration:
    """Integration tests for connector interfaces"""
    
    def test_connector_hierarchy(self):
        """Test that connector hierarchy is properly structured"""
        # ReadWriteConnector should inherit from Pulse, Readable, and Writable
        assert issubclass(ReadWriteConnector, Pulse)
        assert issubclass(ReadWriteConnector, Readable)
        assert issubclass(ReadWriteConnector, Writable)
        
        # ReadOnlyConnector should inherit from Pulse and Readable
        assert issubclass(ReadOnlyConnector, Pulse)
        assert issubclass(ReadOnlyConnector, Readable)
        
        # WriteOnlyConnector should inherit from Pulse and Writable
        assert issubclass(WriteOnlyConnector, Pulse)
        assert issubclass(WriteOnlyConnector, Writable)
        
        # All connectors should inherit from Pulse (the base interface)
        assert issubclass(ReadOnlyConnector, Pulse)
        assert issubclass(WriteOnlyConnector, Pulse)
        assert issubclass(ReadWriteConnector, Pulse)
    
    def test_connector_method_signatures(self):
        """Test that connector methods have consistent signatures"""
        # All query methods should accept query string and optional params
        read_methods = ['execute_query', 'fetch_one', 'fetch_all']
        write_methods = ['execute_write', 'execute_batch']
        
        # Test that these methods exist on the appropriate interfaces
        for method in read_methods:
            assert hasattr(ReadOnlyConnector, method)
            assert hasattr(ReadWriteConnector, method)
        
        for method in write_methods:
            assert hasattr(WriteOnlyConnector, method)
            assert hasattr(ReadWriteConnector, method)
        
        # Test that transaction methods exist on write interfaces
        transaction_methods = ['begin_transaction', 'commit_transaction', 'rollback_transaction']
        for method in transaction_methods:
            assert hasattr(WriteOnlyConnector, method)
            assert hasattr(ReadWriteConnector, method)



