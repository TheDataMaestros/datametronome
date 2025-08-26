.PHONY: help install install-dev install-test install-docs clean test test-unit test-integration test-cov lint format type-check security-check build publish docs docs-serve clean-build clean-pyc clean-test clean-docs

# Default target
help:
	@echo "DataPulse Core - Development Commands"
	@echo "====================================="
	@echo ""
	@echo "Installation:"
	@echo "  install          Install package in development mode"
	@echo "  install-dev      Install development dependencies"
	@echo "  install-test     Install test dependencies"
	@echo "  install-docs     Install documentation dependencies"
	@echo ""
	@echo "Development:"
	@echo "  format           Format code with black and isort"
	@echo "  lint             Run linting checks"
	@echo "  type-check       Run type checking with mypy"
	@echo "  security-check   Run security checks"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-cov         Run tests with coverage"
	@echo ""
	@echo "Documentation:"
	@echo "  docs             Build documentation"
	@echo "  docs-serve       Serve documentation locally"
	@echo ""
	@echo "Package Management:"
	@echo "  build            Build package distribution"
	@echo "  publish          Publish to PyPI (requires PYPI_API_TOKEN)"
	@echo ""
	@echo "Cleaning:"
	@echo "  clean            Clean all build artifacts"
	@echo "  clean-build      Clean build artifacts"
	@echo "  clean-pyc        Clean Python cache files"
	@echo "  clean-test       Clean test artifacts"
	@echo "  clean-docs       Clean documentation build"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-test:
	pip install -e ".[test]"

install-docs:
	pip install -e ".[docs]"

# Development targets
format:
	black metronome_pulse_core tests
	isort metronome_pulse_core tests

lint:
	black --check --diff metronome_pulse_core tests
	isort --check-only --diff metronome_pulse_core tests
	ruff check metronome_pulse_core tests

type-check:
	mypy metronome_pulse_core

security-check:
	bandit -r metronome_pulse_core -f json -o bandit-report.json
	safety check

# Testing targets
test:
	pytest

test-unit:
	pytest -m "unit"

test-integration:
	pytest -m "integration"

test-cov:
	pytest --cov=metronome_pulse_core --cov-report=html --cov-report=term-missing

# Documentation targets
docs:
	cd docs && make html

docs-serve:
	cd docs && python -m http.server 8000 -d _build/html

# Package management targets
build:
	python -m build

publish: build
	twine upload dist/*

# Cleaning targets
clean: clean-build clean-pyc clean-test clean-docs

clean-build:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

clean-pyc:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

clean-test:
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf bandit-report.json

clean-docs:
	cd docs && make clean

# Pre-commit hooks
install-hooks:
	pre-commit install

update-hooks:
	pre-commit autoupdate

run-hooks:
	pre-commit run --all-files

# Development workflow
dev-setup: install-dev install-hooks
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify installation"

# Quick development cycle
dev-cycle: format lint type-check test
	@echo "Development cycle complete!"

# Release preparation
release-prep: clean format lint type-check test-cov build
	@echo "Release preparation complete!"
	@echo "Run 'make publish' to publish to PyPI"

# Docker development
docker-build:
	docker build -t metronome-pulse-core:dev .

docker-test:
	docker run --rm metronome-pulse-core:dev make test

docker-shell:
	docker run --rm -it metronome-pulse-core:dev /bin/bash

# Performance testing
benchmark:
	pytest --benchmark-only

# Coverage report
coverage-report: test-cov
	@echo "Coverage report generated in htmlcov/index.html"
	@echo "Open htmlcov/index.html in your browser to view"

# Dependency management
update-deps:
	pip install --upgrade pip setuptools wheel
	pip install --upgrade -r requirements-dev.txt

check-deps:
	pip list --outdated

# Quality gates
quality-gate: format lint type-check security-check test-cov
	@echo "✅ All quality checks passed!"
	@echo "🚀 Ready for commit and push!"

# Help for specific targets
help-format:
	@echo "Formatting Commands:"
	@echo "  make format          - Format all Python files"
	@echo "  make lint            - Check formatting without changing files"
	@echo "  make type-check      - Run type checking"

help-test:
	@echo "Testing Commands:"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run unit tests only"
	@echo "  make test-integration- Run integration tests only"
	@echo "  make test-cov        - Run tests with coverage report"

help-release:
	@echo "Release Commands:"
	@echo "  make release-prep    - Prepare for release (format, lint, test, build)"
	@echo "  make build           - Build package distribution"
	@echo "  make publish         - Publish to PyPI (requires PYPI_API_TOKEN)"



