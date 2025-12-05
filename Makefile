# Neo4j Filter Service Makefile

.PHONY: help install dev run test lint format clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies with UV"
	@echo "  dev          - Install dev dependencies"
	@echo "  run          - Run the application locally"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linter (ruff)"
	@echo "  format       - Format code (black)"
	@echo "  clean        - Clean cache and build files"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-up    - Start services with docker-compose"
	@echo "  docker-down  - Stop services"

install:
	uv sync

dev:
	uv sync --dev

run:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest -v

lint:
	uv run ruff check app/

format:
	uv run black app/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-build:
	docker build -t neo4j-filter-service .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f filter_service