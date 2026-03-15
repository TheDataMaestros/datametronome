.PHONY: help up up-workers down test migrate logs

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Start the full stack (podium + postgres + redis + rabbitmq + UI)
	docker-compose --profile full up -d --build

up-workers: ## Start full stack + Celery worker + Beat scheduler
	docker-compose --profile full --profile worker up -d --build

down: ## Stop all services and clean up
	docker-compose --profile full --profile worker down

test: ## Run tests locally via .venv (fast, uses SQLite)
	cd datametronome/podium && .venv/bin/python -m pytest --timeout=10 -q $(ARGS)

migrate: ## Run Alembic migrations inside Docker
	docker-compose exec podium sh -c "cd /app/datametronome/podium && DATABASE_URL=\$$DATAMETRONOME_DATABASE_URL alembic upgrade head"

logs: ## Tail docker-compose logs (use ARGS=podium to filter)
	docker-compose logs -f $(ARGS)
