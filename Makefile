.PHONY: help dev prod build clean logs db-init db-shell db-backup db-restore db-health test test-content-extraction format lint

# Default target
.DEFAULT_GOAL := help

# Color output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Trading Report Automation System - Make Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Development & Deployment:$(NC)"
	@grep -E '^\s*make|^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | grep -v '@echo' | sed 's/make //' | awk 'BEGIN {FS = ":.*?## "} {printf "  $(BLUE)%-25s$(NC) %s\n", $$1, $$2}' | grep -v '^  make'
	@echo ""
	@echo "$(GREEN)Database:$(NC)"
	@echo "  $(BLUE)db-init$(NC)              Initialize PostgreSQL database and apply schema"
	@echo "  $(BLUE)db-shell$(NC)             Open PostgreSQL shell as trading_user"
	@echo "  $(BLUE)db-backup$(NC)            Backup database to dump file"
	@echo "  $(BLUE)db-restore$(NC)           Restore database from backup"
	@echo "  $(BLUE)db-health$(NC)            Check database connectivity and health"
	@echo "  $(BLUE)db-stats$(NC)             Show database statistics"
	@echo "  $(BLUE)db-vacuum$(NC)            Vacuum and analyze tables"
	@echo "  $(BLUE)db-logs-archive$(NC)      Archive old system logs (>30 days)"
	@echo ""
	@echo "$(GREEN)Container Management:$(NC)"
	@echo "  $(BLUE)dev$(NC)                  Start services with logs visible (development)"
	@echo "  $(BLUE)prod$(NC)                 Start services in background (production mode)"
	@echo "  $(BLUE)build$(NC)                Build/rebuild service images"
	@echo "  $(BLUE)stop$(NC)                 Stop all running services"
	@echo "  $(BLUE)clean$(NC)                Stop and remove containers, volumes"
	@echo "  $(BLUE)logs$(NC)                 Show logs from all services"
	@echo "  $(BLUE)logs-SERVICE=$(NC)service Show logs from specific service"
	@echo ""
	@echo "$(GREEN)Testing & Code Quality:$(NC)"
	@echo "  $(BLUE)test$(NC)                 Run all tests"
	@echo "  $(BLUE)test-schema$(NC)          Run schema validation tests only"
	@echo "  $(BLUE)test-data$(NC)            Run data flow integration tests only"
	@echo "  $(BLUE)test-content-extraction$(NC)  Run content extraction tests"
	@echo "  $(BLUE)format$(NC)               Format Python code (black)"
	@echo "  $(BLUE)lint$(NC)                 Lint Python code (pylint, flake8)"
	@echo "  $(BLUE)typecheck$(NC)            Type check Python code (mypy)"
	@echo ""

# Development targets
dev: ## Start services with visible logs (development)
	@echo "$(GREEN)Starting services in development mode...$(NC)"
	docker-compose up

prod: ## Start services in background (production)
	@echo "$(GREEN)Starting services in background...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started. Check status with: make logs$(NC)"

build: ## Build/rebuild service Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	docker-compose build

stop: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	docker-compose stop

clean: ## Stop and remove containers, volumes
	@echo "$(RED)Removing containers and volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)Cleanup complete$(NC)"

logs: ## Show logs from all services
	docker-compose logs -f

logs-service: ## Show logs from specific service (usage: make logs-service SERVICE=postgres)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)Error: SERVICE not specified$(NC)"; \
		echo "Usage: make logs-service SERVICE=postgres"; \
		exit 1; \
	fi
	docker-compose logs -f $(SERVICE)

# Database targets
db-init: ## Initialize database and apply schema
	@echo "$(GREEN)Initializing database...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)Error: .env file not found$(NC)"; \
		echo "Please copy .env.example to .env and configure database credentials"; \
		exit 1; \
	fi
	docker-compose exec -T postgres python3 /docker-entrypoint-initdb.d/run_migrations.py

db-shell: ## Open PostgreSQL shell as trading_user
	@if [ ! -f .env ]; then \
		echo "$(RED).env file not found$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Connecting to database...$(NC)"
	docker-compose exec postgres psql -U trading_user -d trading_reports

db-health: ## Check database health and connectivity
	@echo "$(BLUE)Checking database health...$(NC)"
	docker-compose exec -T postgres psql -U postgres -d trading_reports -c "SELECT version();"
	docker-compose exec -T postgres psql -U postgres -d trading_reports -c \
		"SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
	@echo "$(GREEN)Database health check complete$(NC)"

db-stats: ## Show database statistics and sizes
	@echo "$(BLUE)Database statistics...$(NC)"
	docker-compose exec -T postgres psql -U postgres -d trading_reports -c \
		"SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables WHERE schemaname='public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

db-vacuum: ## Vacuum and analyze tables
	@echo "$(YELLOW)Running VACUUM ANALYZE...$(NC)"
	docker-compose exec -T postgres psql -U postgres -d trading_reports -c "VACUUM ANALYZE;"
	@echo "$(GREEN)Vacuum complete$(NC)"

db-backup: ## Backup database to file (usage: make db-backup BACKUP_FILE=backup.sql)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		BACKUP_FILE="trading_reports_$$(date +%Y%m%d_%H%M%S).sql"; \
	fi
	@echo "$(GREEN)Backing up database to $(BACKUP_FILE)...$(NC)"
	docker-compose exec -T postgres pg_dump -U postgres -d trading_reports > "$(BACKUP_FILE)"
	@echo "$(GREEN)Backup complete: $(BACKUP_FILE)$(NC)"

db-restore: ## Restore database from backup (usage: make db-restore BACKUP_FILE=backup.sql)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "$(RED)Error: BACKUP_FILE not specified$(NC)"; \
		echo "Usage: make db-restore BACKUP_FILE=backup.sql"; \
		exit 1; \
	fi
	@if [ ! -f "$(BACKUP_FILE)" ]; then \
		echo "$(RED)Error: Backup file not found: $(BACKUP_FILE)$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restoring database from $(BACKUP_FILE)...$(NC)"
	docker-compose exec -T postgres psql -U postgres -d trading_reports < "$(BACKUP_FILE)"
	@echo "$(GREEN)Restore complete$(NC)"

db-logs-archive: ## Archive system logs older than 30 days
	@echo "$(YELLOW)Archiving old logs...$(NC)"
	docker-compose exec -T postgres psql -U trading_user -d trading_reports -c \
		"INSERT INTO system_logs_archive SELECT * FROM system_logs WHERE created_at < NOW() - INTERVAL '30 days'; DELETE FROM system_logs WHERE created_at < NOW() - INTERVAL '30 days';"
	@echo "$(GREEN)Log archival complete$(NC)"

# Testing targets
test: ## Run all tests (schema structure + data flow)
	@echo "$(GREEN)Running all tests...$(NC)"
	python -m pytest postgres/tests/ -v

test-schema: ## Run schema structure validation tests
	@echo "$(GREEN)Running schema validation tests...$(NC)"
	python -m pytest postgres/tests/test_schema_structure.py -v

test-data: ## Run data flow integration tests
	@echo "$(GREEN)Running data flow tests...$(NC)"
	python -m pytest postgres/tests/test_data_flow.py -v

test-content-extraction: ## Run content extraction module tests
	@echo "$(GREEN)Running content extraction tests...$(NC)"
	cd services/playwright-scraper && python -m pytest tests/test_content_extraction_*.py tests/test_content_extractor.py tests/test_scraper_extraction_integration.py -v

# Code quality targets
format: ## Format Python code with black
	@echo "$(BLUE)Formatting Python code...$(NC)"
	python -m black postgres/ services/ --line-length=100

lint: ## Lint Python code (flake8, pylint)
	@echo "$(BLUE)Linting Python code...$(NC)"
	python -m flake8 postgres/ services/ --max-line-length=100 --ignore=E501
	python -m pylint postgres/ services/ --disable=C0111,C0103 || true

typecheck: ## Type check Python code with mypy
	@echo "$(BLUE)Type checking Python code...$(NC)"
	python -m mypy postgres/ services/ --ignore-missing-imports || true

# Utility targets
health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@docker-compose ps
	@echo ""
	@echo "$(BLUE)PostgreSQL health:$(NC)"
	@docker-compose exec -T postgres pg_isready -U postgres || echo "PostgreSQL not responding"
	@echo ""
	@echo "$(BLUE)N8N health:$(NC)"
	@docker-compose exec -T n8n wget -q --spider http://localhost:5678 && echo "N8N is running" || echo "N8N not responding"

shell: ## Open shell in running service (usage: make shell SERVICE=postgres)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)Error: SERVICE not specified$(NC)"; \
		echo "Usage: make shell SERVICE=postgres"; \
		exit 1; \
	fi
	docker-compose exec $(SERVICE) bash

# Lifecycle targets
.env:
	@echo "$(YELLOW)Creating .env from .env.example...$(NC)"
	cp .env.example .env
	@echo "$(RED)WARNING: Please edit .env and set all required credentials!$(NC)"

setup: .env ## Setup project (copy .env, build images)
	@echo "$(GREEN)Running setup...$(NC)"
	$(MAKE) build
	@echo "$(GREEN)Setup complete! Run 'make dev' to start services$(NC)"
