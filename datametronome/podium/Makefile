.PHONY: test test-unit test-integration test-cov test-unit-cov test-integration-cov clean install install-dev lint

# Default target - run unit tests (MOST IMPORTANT)
all: test-unit

# Install dependencies
install:
	pip install -r requirements-test.txt

# Install in development mode
install-dev:
	pip install -e .

# Run ALL tests (unit + integration)
test:
	pytest tests/ -v

# Run ONLY unit tests (MOST IMPORTANT - no external dependencies)
test-unit:
	pytest tests/test_unit.py -v -m "unit"

# Run ONLY integration tests (require database)
test-integration:
	pytest tests/test_integration_database.py -v -m "integration"

# Run API integration tests
test-api:
	pytest tests/test_api_integration.py -v -m "api"

# Run tests with coverage for all
test-cov:
	pytest tests/ --cov=datametronome_podium --cov-report=html --cov-report=term-missing

# Run unit tests with coverage
test-unit-cov:
	pytest tests/test_unit.py -m "unit" --cov=datametronome_podium --cov-report=html --cov-report=term-missing

# Run integration tests with coverage
test-integration-cov:
	pytest tests/test_integration_database.py -m "integration" --cov=datametronome_podium --cov-report=html --cov-report=term-missing

# Run slow tests
test-slow:
	pytest tests/ -m "slow" -v

# Run database tests
test-database:
	pytest tests/ -m "database" -v

# Lint code
lint:
	flake8 datametronome_podium/
	black --check datametronome_podium/
	isort --check-only datametronome_podium/

# Format code
format:
	black datametronome_podium/
	isort datametronome_podium/

# Clean up
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

# Help
help:
	@echo "Available targets:"
	@echo "  test-unit        - Run ONLY unit tests (MOST IMPORTANT - no external deps)"
	@echo "  test-integration - Run ONLY integration tests (require database)"
	@echo "  test-api         - Run API integration tests"
	@echo "  test             - Run ALL tests"
	@echo "  test-cov         - Run all tests with coverage"
	@echo "  test-unit-cov    - Run unit tests with coverage"
	@echo "  test-integration-cov - Run integration tests with coverage"
	@echo "  test-slow        - Run slow tests"
	@echo "  test-database    - Run database tests"
	@echo "  install          - Install test dependencies"
	@echo "  install-dev      - Install in development mode"
	@echo "  lint             - Check code quality"
	@echo "  format           - Format code"
	@echo "  clean            - Clean up generated files"
	@echo "  help             - Show this help message"
	@echo ""
	@echo "NOTE: Unit tests are the MOST IMPORTANT tests and should run first!"
	@echo "      They test individual components without external dependencies."
