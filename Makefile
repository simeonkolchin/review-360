.DEFAULT_GOAL := help
COMPOSE := docker compose
BASE_URL ?= http://localhost:8080/api
BOT_TOKEN ?= $(shell grep -E '^BOT_API_TOKEN=' .env 2>/dev/null | cut -d= -f2)

.PHONY: help env up up-bot down restart build logs logs-bot ps test shell-db reset spec fmt

help: ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from the template if it is missing
	@test -f .env || (cp .env.example .env && echo "created .env — put your bot token in it")

up: env ## Start everything except the bot (web + api + db)
	$(COMPOSE) up -d --build
	@echo "→ http://localhost:$${PUBLIC_PORT:-8080}"

up-bot: env ## Start everything including the Telegram bot
	$(COMPOSE) --profile bot up -d --build

down: ## Stop all containers
	$(COMPOSE) --profile bot down

restart: ## Recreate the app containers, keeping the database
	$(COMPOSE) --profile bot up -d --build --force-recreate gateway data-service bot frontend

build: ## Rebuild images without starting
	$(COMPOSE) --profile bot build

logs: ## Tail gateway + data-service logs
	$(COMPOSE) logs -f gateway data-service

logs-bot: ## Tail bot logs
	$(COMPOSE) logs -f bot

ps: ## Show container status
	$(COMPOSE) --profile bot ps

test: ## Run the end-to-end flow test against a running stack
	python3 tests/run_flow_test.py --base-url $(BASE_URL) --bot-token $(BOT_TOKEN)

shell-db: ## Open psql inside the database container
	$(COMPOSE) exec postgres psql -U $${DB_USER:-review360} -d $${DB_NAME:-review360}

spec: ## Refresh the OpenAPI specs (services write them on boot)
	$(COMPOSE) restart gateway data-service
	@ls -1 openapi_spec

reset: ## Drop the database volume and start clean — destroys all data
	$(COMPOSE) --profile bot down -v
	$(COMPOSE) up -d --build
