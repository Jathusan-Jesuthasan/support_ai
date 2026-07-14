# =====================================================================
# SupportAI Backend Automation Makefile
# =====================================================================

.PHONY: install test lint run docker-build docker-up docker-down help

help:
	@echo "Available commands:"
	@echo "  install      - Install application dependencies"
	@echo "  test         - Run pytest suite"
	@echo "  lint         - Check code style and static analysis (ruff and mypy)"
	@echo "  run          - Start local uvicorn application server"
	@echo "  docker-build - Build application Docker image"
	@echo "  docker-up    - Run all compose network services in background"
	@echo "  docker-down  - Tear down all compose network services"

install:
	pip install -r requirements.txt

test:
	pytest -v

lint:
	ruff check .
	mypy .

run:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
