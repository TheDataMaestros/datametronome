"""
Example-driven unit tests for Staves and Clefs.

These tests serve as DOCUMENTATION and EXAMPLES for developers.
They show how to create, use, and work with Staves (data sources) and
Clefs (data quality checks) in DataMetronome.

Run these tests to understand the API:
    pytest tests/test_stave_examples.py -v
"""

import json
from datetime import datetime

import pytest
from datametronome_podium.models.clef import SUPPORTED_CHECK_TYPES, Clef
from datametronome_podium.models.stave import SUPPORTED_DATA_SOURCES, Stave
from datametronome_podium.services.stave_service import (
    create_clef,
    create_mysql_stave,
    create_null_check,
    create_postgres_stave,
    create_range_check,
    create_sqlite_stave,
    create_stave,
    create_volume_check,
    deserialize_clef,
    deserialize_stave,
    generate_clef_id,
    generate_stave_id,
    is_valid_check_type,
    is_valid_data_source_type,
    serialize_clef,
    serialize_stave,
)


class TestStaveCreationExamples:
    """
    Examples showing different ways to create Staves.

    A Stave is a data source you want to monitor. These tests show
    you how to create staves for different database types.
    """

    def test_create_postgres_stave_example(self):
        """Example: Create a PostgreSQL stave for monitoring."""
        # This is the easiest way to create a PostgreSQL stave
        stave = create_postgres_stave(
            name="Production Database",
            host="db.example.com",
            database="prod_db",
            user="monitor_user",
            password="secure_password",
            port=5432,
            description="Main production database for user data",
        )

        # Verify it was created correctly
        assert stave.name == "Production Database"
        assert stave.data_source_type == "postgres"
        assert stave.connection_config["host"] == "db.example.com"
        assert stave.connection_config["port"] == 5432
        assert stave.connection_config["database"] == "prod_db"
        assert stave.connection_config["user"] == "monitor_user"
        assert stave.is_active is True
        assert stave.id is not None  # Auto-generated ID
        assert isinstance(stave.created_at, datetime)

        # You can print it for debugging
        print(f"\nCreated: {stave}")
        # Output: 🟢 Active Production Database (postgres)

    def test_create_sqlite_stave_example(self):
        """Example: Create a SQLite stave for local databases."""
        stave = create_sqlite_stave(
            name="Local Analytics DB",
            path="/data/analytics.db",
            description="Local SQLite database for analytics",
        )

        assert stave.name == "Local Analytics DB"
        assert stave.data_source_type == "sqlite"
        assert stave.connection_config["path"] == "/data/analytics.db"
        assert stave.is_active is True
        print(f"\nCreated: {stave}")

    def test_create_mysql_stave_example(self):
        """Example: Create a MySQL stave."""
        stave = create_mysql_stave(
            name="MySQL Application DB",
            host="mysql.example.com",
            database="app_db",
            user="readonly_user",
            password="password123",
            port=3306,
        )

        assert stave.name == "MySQL Application DB"
        assert stave.data_source_type == "mysql"
        assert stave.connection_config["host"] == "mysql.example.com"
        assert stave.connection_config["port"] == 3306
        print(f"\nCreated: {stave}")

    def test_create_generic_stave_example(self):
        """Example: Create a stave for any data source type."""
        # For more control, use the generic create_stave function
        stave = create_stave(
            name="Redis Cache",
            data_source_type="redis",
            connection_config={"host": "redis.example.com", "port": 6379, "db": 0},
            description="Production Redis cache",
            is_active=True,
        )

        assert stave.name == "Redis Cache"
        assert stave.data_source_type == "redis"
        assert stave.connection_config["host"] == "redis.example.com"
        print(f"\nCreated: {stave}")

    def test_inactive_stave_example(self):
        """Example: Create an inactive stave (monitoring paused)."""
        stave = create_sqlite_stave(name="Old Test DB", path="/tmp/old_test.db")
        # Deactivate it
        stave.is_active = False

        assert stave.is_active is False
        print(f"\nCreated: {stave}")
        # Output: 🔴 Inactive Old Test DB (sqlite)


class TestStaveValidationExamples:
    """
    Examples showing what makes a valid or invalid Stave.

    These tests help you understand the validation rules.
    """

    def test_valid_stave_minimal_example(self):
        """Example: Minimal valid stave."""
        # This is the minimum you need to create a stave
        stave = Stave(
            name="Test DB",
            data_source_type="postgres",
            connection_config={"host": "localhost"},
        )

        assert stave.name == "Test DB"
        # Defaults are set automatically
        assert stave.is_active is True
        assert stave.created_at is not None

    def test_invalid_stave_empty_name(self):
        """Example: Staves must have a non-empty name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Stave(
                name="   ",  # Whitespace only
                data_source_type="postgres",
                connection_config={"host": "localhost"},
            )

    def test_invalid_stave_unsupported_type(self):
        """Example: Data source type must be supported."""
        with pytest.raises(ValueError, match="Unsupported data source type"):
            Stave(
                name="Test DB",
                data_source_type="oracle",  # Not supported (yet!)
                connection_config={"host": "localhost"},
            )

    def test_invalid_stave_empty_config(self):
        """Example: Connection config cannot be empty."""
        with pytest.raises(ValueError, match="connection_config cannot be empty"):
            Stave(
                name="Test DB",
                data_source_type="postgres",
                connection_config={},  # Empty config
            )

    def test_stave_case_insensitive_type(self):
        """Example: Data source types are case-insensitive."""
        stave1 = Stave(
            name="DB 1",
            data_source_type="POSTGRES",  # Uppercase
            connection_config={"host": "localhost"},
        )
        stave2 = Stave(
            name="DB 2",
            data_source_type="postgres",  # Lowercase
            connection_config={"host": "localhost"},
        )

        # Both are normalized to lowercase
        assert stave1.data_source_type == "postgres"
        assert stave2.data_source_type == "postgres"


class TestClefCreationExamples:
    """
    Examples showing different ways to create Clefs (data quality checks).

    A Clef is a data quality check that runs against a Stave. These tests
    show you how to create different types of checks.
    """

    def test_create_null_check_example(self):
        """Example: Check for NULL values in a column."""
        # Create a check that ensures email column has no NULLs
        check = create_null_check(
            stave_id="stave-123",
            name="Email NULL Check",
            table="users",
            column="email",
            threshold=0.0,  # 0% NULLs allowed
            schedule="@hourly",  # Run every hour
        )

        assert check.name == "Email NULL Check"
        assert check.check_type == "column_values"
        assert check.config["table"] == "users"
        assert check.config["column"] == "email"
        assert check.config["condition"] == "if_null"
        assert check.fail == "if_null > 0%"
        assert check.schedule == "@hourly"
        print(f"\nCreated: {check}")
        # Output: 🟢 Active Email NULL Check (null_check, scheduled: @hourly)

    def test_create_range_check_example(self):
        """Example: Check if values are within an expected range."""
        # Create a check that ensures age is between 0 and 150
        check = create_range_check(
            stave_id="stave-123",
            name="Age Range Validation",
            table="users",
            column="age",
            min_value=0,
            max_value=150,
            schedule="0 */6 * * *",  # Every 6 hours
        )

        assert check.name == "Age Range Validation"
        assert check.check_type == "column_values"
        assert check.config["min"] == 0
        assert check.config["max"] == 150
        print(f"\nCreated: {check}")

    def test_create_volume_check_example(self):
        """Example: Check if table has expected number of rows."""
        # Create a check that ensures events table has reasonable volume
        check = create_volume_check(
            stave_id="stave-123",
            name="Daily Events Volume",
            table="events",
            expected_min=1000,
            expected_max=100000,
            schedule="@daily",
        )

        assert check.name == "Daily Events Volume"
        assert check.check_type == "row_count"
        assert check.config["expected_min"] == 1000
        assert check.config["expected_max"] == 100000
        print(f"\nCreated: {check}")

    def test_create_custom_check_example(self):
        """Example: Create a custom check with specific config."""
        # For more control, use the generic create_clef function
        check = create_clef(
            stave_id="stave-123",
            name="Email Format Check",
            check_type="column_values",
            config={
                "table": "users",
                "column": "email",
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            },
            description="Validate email addresses match expected format",
            schedule="0 2 * * *",  # Daily at 2 AM
        )

        assert check.name == "Email Format Check"
        assert check.check_type == "column_values"
        assert "pattern" in check.config
        print(f"\nCreated: {check}")


class TestSerializationExamples:
    """
    Examples showing how to save/load Staves and Clefs to/from the database.

    When storing in SQLite, connection_config is stored as a JSON TEXT field.
    These helpers make serialization easy.
    """

    def test_serialize_stave_for_database_example(self):
        """Example: Prepare a stave for database storage."""
        # Create a stave
        stave = create_postgres_stave(
            name="Production DB", host="db.example.com", database="prod", user="monitor"
        )

        # Serialize it for database storage
        db_data = serialize_stave(stave)

        # connection_config is now a JSON string
        assert isinstance(db_data["connection_config"], str)
        assert isinstance(db_data["created_at"], str)
        assert isinstance(db_data["updated_at"], str)

        # You can now insert this into the database
        print("\nDatabase row data:")
        print(json.dumps(db_data, indent=2))

        # The connection_config is a JSON string
        config_dict = json.loads(db_data["connection_config"])
        assert config_dict["host"] == "db.example.com"

    def test_deserialize_stave_from_database_example(self):
        """Example: Load a stave from database storage."""
        # Simulate data from database (connection_config is JSON string)
        db_row = {
            "id": "stave-abc123",
            "name": "Production DB",
            "description": "Main database",
            "data_source_type": "postgres",
            "connection_config": json.dumps(
                {
                    "host": "db.example.com",
                    "port": 5432,
                    "database": "prod",
                    "user": "monitor",
                }
            ),
            "is_active": True,
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:00:00",
        }

        # Deserialize it back to a Stave object
        stave = deserialize_stave(db_row)

        # Now you have a proper Stave object
        assert isinstance(stave, Stave)
        assert stave.name == "Production DB"
        assert stave.connection_config["host"] == "db.example.com"
        assert isinstance(stave.created_at, datetime)

        print(f"\nDeserialized: {stave}")

    def test_serialize_clef_for_database_example(self):
        """Example: Prepare a clef for database storage."""
        check = create_null_check(
            stave_id="stave-123", name="Email Check", table="users", column="email"
        )

        # Serialize for database
        db_data = serialize_clef(check)

        # config is now a JSON string
        assert isinstance(db_data["config"], str)
        assert isinstance(db_data["created_at"], str)

        print("\nDatabase row data:")
        print(json.dumps(db_data, indent=2))

    def test_roundtrip_serialization_example(self):
        """Example: Full roundtrip - create, save, load."""
        # 1. Create a stave
        original = create_postgres_stave(
            name="Test DB", host="localhost", database="test", user="test_user"
        )

        # 2. Serialize for database
        db_data = serialize_stave(original)

        # 3. Simulate database storage/retrieval
        # (In real code, you'd INSERT this into database and SELECT it back)

        # 4. Deserialize back to Stave
        loaded = deserialize_stave(db_data)

        # 5. Verify it's the same
        assert loaded.name == original.name
        assert loaded.data_source_type == original.data_source_type
        assert loaded.connection_config == original.connection_config

        print(f"\nOriginal: {original}")
        print(f"Loaded:   {loaded}")


class TestHelperFunctionsExamples:
    """
    Examples showing useful helper functions.
    """

    def test_generate_unique_ids_example(self):
        """Example: Generate unique IDs for staves and clefs."""
        # Generate stave IDs
        id1 = generate_stave_id()
        id2 = generate_stave_id()

        assert id1.startswith("stave-")
        assert id2.startswith("stave-")
        assert id1 != id2  # Unique

        # Generate clef IDs
        id3 = generate_clef_id()
        assert id3.startswith("clef-")

        print(f"\nGenerated IDs:")
        print(f"  Stave 1: {id1}")
        print(f"  Stave 2: {id2}")
        print(f"  Clef 1:  {id3}")

    def test_validation_helpers_example(self):
        """Example: Check if types are supported."""
        # Check data source types
        assert is_valid_data_source_type("postgres") is True
        assert is_valid_data_source_type("oracle") is False

        # Check check types
        assert is_valid_check_type("column_values") is True
        assert is_valid_check_type("custom_check") is False

        # Get all supported types
        print("\nSupported data sources:", SUPPORTED_DATA_SOURCES)
        print("Supported check types:", SUPPORTED_CHECK_TYPES)


class TestRealWorldScenarioExamples:
    """
    Real-world scenarios showing how to use Staves and Clefs together.
    """

    def test_setup_monitoring_for_new_database(self):
        """
        Example: Complete setup for monitoring a new database.

        Scenario: You have a new production database and want to monitor it.
        """
        # Step 1: Create the stave (data source)
        stave = create_postgres_stave(
            name="Production User Database",
            host="prod-db.company.com",
            database="users_prod",
            user="monitor_readonly",
            password="secure_password_123",
            description="Main production database storing user accounts and profiles",
        )

        print(f"\n📊 Created stave: {stave}")

        # Step 2: Create checks for critical columns
        checks = []

        # Check 1: Ensure emails are not NULL
        checks.append(
            create_null_check(
                stave_id=stave.id,
                name="User Email Required",
                table="users",
                column="email",
                threshold=0.0,  # No NULLs allowed
                schedule="@hourly",
            )
        )

        # Check 2: Ensure ages are reasonable
        checks.append(
            create_range_check(
                stave_id=stave.id,
                name="User Age Range",
                table="users",
                column="age",
                min_value=0,
                max_value=150,
                schedule="@daily",
            )
        )

        # Check 3: Ensure minimum user count
        checks.append(
            create_volume_check(
                stave_id=stave.id,
                name="Minimum User Count",
                table="users",
                expected_min=1000,
                schedule="0 8 * * *",  # Daily at 8 AM
            )
        )

        print(f"\n✅ Created {len(checks)} checks:")
        for check in checks:
            print(f"  - {check}")

        # Step 3: Serialize everything for database storage
        stave_data = serialize_stave(stave)
        checks_data = [serialize_clef(check) for check in checks]

        # Now you would INSERT these into your database
        assert stave_data["id"] == stave.id
        assert len(checks_data) == 3

        print(f"\n💾 Ready to save to database:")
        print(f"  - 1 stave")
        print(f"  - {len(checks_data)} clefs")
