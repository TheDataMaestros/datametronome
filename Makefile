.PHONY: help install install-dev install-podium test lint format clean docker-up docker-down docker-build prototype docker-prototype retail-db

help: ## Show this help message
	@echo "DataMetronome - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all packages in development mode
	uv pip install -e ./datametronome/podium
	uv pip install -e ./datametronome/pulse/core
	uv pip install -e ./datametronome/pulse/sqlite
	uv pip install -e ./datametronome/brain/base

install-podium: ## Install Podium runtime dependencies only
	@if command -v uv >/dev/null 2>&1; then \
		uv pip install -e ./datametronome/pulse/core -e ./datametronome/pulse/sqlite -e ./datametronome/brain/base -e ./datametronome/podium; \
	else \
		python3 -m pip install -e ./datametronome/pulse/core -e ./datametronome/pulse/sqlite -e ./datametronome/brain/base -e ./datametronome/podium; \
	fi

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
	@echo "🚀 Backend: http://localhost:8001"
	@echo "🎨 UI: run 'npm run dev' inside ui-nuxt/ (default port 3000)"
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

start-podium: install-podium ## Start the Podium backend
	./start_podium.sh

start-ui: ## Start the UI
	@bash -c 'set -a; [ -f config.env ] && source config.env; set +a; \
	cd ui-nuxt && npm install && \
	NUXT_PUBLIC_API_BASE="http://127.0.0.1:$${PODIUM_PORT:-8000}/api/v1" \
	NUXT_PUBLIC_PODIUM_API_BASE="http://127.0.0.1:$${PODIUM_PORT:-8000}" \
	npm run dev -- --port $${UI_PORT:-3000}'

retail-db: ## Generate the Retail demo dataset DB (SQLite)
	@python3 showcase/retail_demo/generate_db.py --out datametronome/podium/data/retail.db

retail-demo-setup: retail-db ## Generate retail DB and historical checks (requires Podium running)
	@echo "📊 Generating historical check results..."
	@python3 showcase/retail_demo/generate_db.py --out datametronome/podium/data/retail.db --generate-historical-checks

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
