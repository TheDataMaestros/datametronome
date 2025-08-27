.PHONY: test test-cov test-unit test-integration clean install install-dev lint

# Default target
all: test

# Install dependencies
install:
	pip install -r requirements-test.txt

# Install in development mode
install-dev:
	pip install -e .

# Run all tests
test:
	pytest tests/ -v

# Run tests with coverage
test-cov:
	pytest tests/ --cov=metronome_pulse_postgres_sqlalchemy --cov-report=html --cov-report=term-missing

# Run only unit tests
test-unit:
	pytest tests/ -m "unit" -v

# Run only integration tests
test-integration:
	pytest tests/ -m "integration" -v

# Run slow tests
test-slow:
	pytest tests/ -m "slow" -v

# Lint code
lint:
	flake8 metronome_pulse_postgres_sqlalchemy/
	black --check metronome_pulse_postgres_sqlalchemy/
	isort --check-only metronome_pulse_postgres_sqlalchemy/

# Format code
format:
	black metronome_pulse_postgres_sqlalchemy/
	isort metronome_pulse_postgres_sqlalchemy/

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
	@echo "  test           - Run all tests"
	@echo "  test-cov       - Run tests with coverage"
	@echo "  test-unit      - Run only unit tests"
	@echo "  test-integration - Run only integration tests"
	@echo "  test-slow      - Run slow tests"
	@echo "  install        - Install test dependencies"
	@echo "  install-dev    - Install in development mode"
	@echo "  lint           - Lint code"
	@echo "  format         - Format code"
	@echo "  clean          - Clean up generated files"
	@echo "  help           - Show this help message"



