.PHONY: help install test lint format clean start stop start-infra stop-infra

help:
	@echo "Retail Multi-Agent AI"
	@echo "  install      Install dependencies"
	@echo "  test         Run test suite"
	@echo "  lint         Run formatting and type checks"
	@echo "  format       Format code"
	@echo "  start        Start services"
	@echo "  stop         Stop services"
	@echo "  start-infra  Start postgres, redis, minio"
	@echo "  stop-infra   Stop infrastructure"

install:
	pip install -r requirements.txt

start-infra:
	docker compose up -d postgres redis minio

stop-infra:
	docker compose stop postgres redis minio

start: start-infra
	python -m src.api.main

test:
	pytest

lint:
	black --check src tests
	isort --check-only src tests
	mypy src

format:
	black src tests
	isort src tests

clean:
	rmdir /s /q __pycache__ 2>nul || exit /b 0
