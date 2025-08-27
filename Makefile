.PHONY: help install install-dev test lint format clean docker-up docker-down docker-build prototype docker-prototype

help: ## Show this help message
	@echo "DataMetronome - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all packages in development mode
	uv pip install -e ./datametronome/podium
	uv pip install -e ./datametronome/ui-streamlit
	uv pip install -e ./datametronome/pulse/core
	uv pip install -e ./datametronome/brain/base

install-dev: ## Install development dependencies
	uv pip install pytest pytest-asyncio black isort mypy

test: ## Run tests
	pytest tests/ -v

lint: ## Run linting
	black --check datametronome/ tests/
	isort --check-only datametronome/ tests/
	mypy datametronome/

format: ## Format code
	black datametronome/ tests/
	isort datametronome/ tests/

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/ dist/ .eggs/

docker-up: ## Start all Docker services
	docker-compose up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-build: ## Build Docker images
	docker-compose build

docker-prototype: ## Quick prototype setup with Docker
	@echo "🐳 Setting up DataMetronome prototype with Docker..."
	$(MAKE) docker-build
	$(MAKE) docker-up
	@echo "🎉 Docker prototype ready!"
	@echo "🚀 Backend: http://localhost:8000"
	@echo "🎨 UI: http://localhost:8501"
	@echo "🔑 Login with: admin / admin"
	@echo ""
	@echo "📊 To see logs: docker-compose logs -f"
	@echo "🛑 To stop: make docker-down"

prototype: ## Quick prototype setup and start (local)
	@echo "Setting up DataMetronome prototype..."
	$(MAKE) install
	$(MAKE) install-dev
	$(MAKE) setup-db
	$(MAKE) init-prototype
	@echo "🎉 Prototype ready!"
	@echo "🚀 Start the backend: make start-podium"
	@echo "🎨 Start the UI: make start-ui"
	@echo "🔑 Login with: admin / admin"

start-podium: ## Start the Podium backend
	cd datametronome/podium && python -m datametronome_podium.main

start-ui: ## Start the Streamlit UI
	cd datametronome/ui-streamlit && streamlit run datametronome_ui_streamlit/main.py

setup-db: ## Initialize the database
	cd datametronome/podium && DATAMETRONOME_SECRET_KEY="dev-secret-key-change-in-production-32-chars" DATAMETRONOME_DATABASE_URL="sqlite+aiosqlite:///$(PWD)/data/datametronome.db" python -c "import asyncio; from datametronome_podium.core.database import init_db; asyncio.run(init_db())"

init-prototype: ## Initialize prototype data
	@echo "⚠️ init-prototype target removed - use community-demo instead"

community-demo: install-dev ## Run DataMetronome Community Demo
	@echo "🎵 Running DataMetronome Community Demo..."
	@echo "Testing the complete ecosystem..."
	@python3 community_demo.py

test-quick: install-dev ## Quick system test
	@echo "🚀 Quick system test..."
	@python3 community_demo.py
