.DEFAULT_GOAL := help

COMPOSE ?= docker compose
APP_PROFILE ?= app
UV ?= uv
UV_RUN ?= $(UV) run
NPM ?= npm
BACKEND_DIR ?= backend
FRONTEND_DIR ?= frontend
BACKEND_PORT ?= 9000

.PHONY: help up down restart ps logs docker-build docker-up docker-down docker-restart docker-ps docker-logs setup install backend-install backend-install-test backend-migrate backend-run backend-test frontend-install frontend-run frontend-build frontend-lint dev test check

help:
	@echo "AI Second Brain targets:"
	@echo "  make up                 Start postgres/redis/qdrant/minio"
	@echo "  make down               Stop docker services"
	@echo "  make restart            Restart docker services"
	@echo "  make ps                 Show docker service status"
	@echo "  make logs               Follow docker service logs"
	@echo "  make docker-build       Build backend/frontend images"
	@echo "  make docker-up          Build and start full stack in Docker"
	@echo "  make docker-down        Stop full stack containers"
	@echo "  make docker-ps          Show full stack service status"
	@echo "  make docker-logs        Follow full stack service logs"
	@echo "  make install            Install backend and frontend deps"
	@echo "  make setup              Install deps and run backend migrations"
	@echo "  make dev                Run backend and frontend locally"
	@echo "  make test               Run backend tests and frontend checks"
	@echo "  make check              Alias for test"
	@echo "  make backend-run        Start FastAPI dev server"
	@echo "  make frontend-run       Start Next.js dev server"

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(MAKE) down
	$(MAKE) up

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

docker-build:
	$(COMPOSE) --profile $(APP_PROFILE) build backend frontend

docker-up:
	$(COMPOSE) --profile $(APP_PROFILE) up -d --build

docker-down:
	$(COMPOSE) down

docker-restart:
	$(MAKE) docker-down
	$(MAKE) docker-up

docker-ps:
	$(COMPOSE) --profile $(APP_PROFILE) ps

docker-logs:
	$(COMPOSE) --profile $(APP_PROFILE) logs -f backend frontend

setup:
	$(MAKE) up
	$(MAKE) install
	$(MAKE) backend-migrate

install:
	$(MAKE) backend-install
	$(MAKE) frontend-install

backend-install:
	cd $(BACKEND_DIR) && $(UV) sync

backend-install-test:
	cd $(BACKEND_DIR) && $(UV) sync --extra test

backend-migrate:
	cd $(BACKEND_DIR) && $(UV_RUN) alembic -c alembic.ini upgrade head

backend-run:
	cd $(BACKEND_DIR) && $(UV_RUN) uvicorn app.main:app --reload --port $(BACKEND_PORT)

backend-test: backend-install-test
	cd $(BACKEND_DIR) && $(UV_RUN) pytest

frontend-install:
	cd $(FRONTEND_DIR) && $(NPM) install

frontend-run:
	cd $(FRONTEND_DIR) && $(NPM) run dev

frontend-build:
	cd $(FRONTEND_DIR) && $(NPM) run build

frontend-lint:
	cd $(FRONTEND_DIR) && $(NPM) run lint

dev:
	$(MAKE) -j2 backend-run frontend-run

test:
	$(MAKE) backend-test
	$(MAKE) frontend-lint
	$(MAKE) frontend-build

check: test
