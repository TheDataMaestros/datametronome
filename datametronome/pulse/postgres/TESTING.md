# Testing Guide for Postgres Datapulse

This datapulse is designed to be completely standalone and self-contained. You can run tests independently without needing the entire datametronome ecosystem.

## Quick Start

```bash
# Install test dependencies
make install

# Run all tests
make test

# Run tests with coverage
make test-cov
```

## Test Structure

The tests are organized as follows:

```
tests/
├── __init__.py
└── test_sql_builder.py
    ├── TestPostgresSQLBuilder          # Unit tests
    └── TestPostgresSQLBuilderIntegration  # Integration tests
```

## Test Categories

### Unit Tests (`test_*` methods)
- **SQL Generation Tests**: Verify SQL query generation for different scenarios
- **Parameter Handling**: Test various parameter combinations and edge cases
- **Session Tuning**: Test session configuration helpers
- **Input Validation**: Test parameter validation and error handling
- **SQL Injection Prevention**: Test security aspects

### Integration Tests (`TestPostgresSQLBuilderIntegration`)
- **Workflow Tests**: Test complete delete workflows
- **Cross-Method Integration**: Test how different methods work together

## Running Specific Test Types

```bash
# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run slow tests
make test-slow

# Run with specific markers
pytest tests/ -m "unit" -v
pytest tests/ -m "integration" -v
```

## Test Coverage

The tests provide comprehensive coverage of:

- ✅ SQL generation for single and multiple rows
- ✅ Multiple column handling
- ✅ Large batch operations
- ✅ Edge cases (zero rows, negative values, etc.)
- ✅ Table and column name handling
- ✅ Session tuning helpers
- ✅ Parameter validation
- ✅ SQL injection prevention
- ✅ Integration workflows

## Development Workflow

```bash
# Install in development mode
make install-dev

# Run tests before committing
make test

# Check code quality
make lint

# Format code
make format

# Clean up generated files
make clean
```

## Dependencies

Test dependencies are minimal and focused:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking support
- `asyncpg` - PostgreSQL driver for async tests

## Standalone Nature

This datapulse can be:
- **Cloned independently** from the main repository
- **Tested in isolation** without other datapulses
- **Deployed separately** as a standalone package
- **Versioned independently** with its own release cycle

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running tests from the datapulse root directory
2. **Missing Dependencies**: Run `make install` to install test requirements
3. **Test Failures**: Check that the underlying SQL builder implementation matches test expectations

### Getting Help

- Check the test output for detailed error messages
- Review the test code to understand expected behavior
- Ensure your environment has the required Python version and dependencies



