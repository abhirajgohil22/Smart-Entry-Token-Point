# Makefile for Smart Campus Token Management System

.PHONY: help install dev-setup test test-fast test-cov lint format clean migrate migrations

help:
	@echo "Smart Campus Token Management System - Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install          Install dependencies"
	@echo "  make dev-setup        Set up development environment"
	@echo ""
	@echo "Running:"
	@echo "  make dev              Run development server"
	@echo "  make docker-dev       Run with Docker Compose"
	@echo ""
	@echo "Database:"
	@echo "  make migrate          Run database migrations"
	@echo "  make migrations       Create database migrations"
	@echo "  make db-reset         Reset database (dev only)"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-fast        Run tests (no migrations)"
	@echo "  make test-cov         Run tests with coverage report"
	@echo "  make test-face        Run only face recognition tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run flake8 linter"
	@echo "  make format           Format code with black and isort"
	@echo "  make security-check   Run bandit security checks"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Clean up generated files"
	@echo "  make requirements     Export requirements.txt"

# Install dependencies
install:
	pip install -r requirements.txt

# Set up development environment
dev-setup: install
	cp .env.example .env
	python manage.py migrate
	python manage.py createsuperuser

# Run development server
dev:
	python manage.py runserver

# Run with Docker Compose
docker-dev:
	docker-compose up

docker-build:
	docker-compose build

docker-shell:
	docker-compose exec django bash

# Database migrations
migrate:
	python manage.py migrate

migrations:
	python manage.py makemigrations

db-reset:
	rm -f db.sqlite3
	python manage.py migrate

# Testing
test:
	pytest --cov=apps --cov-report=html --cov-report=term-missing

test-fast:
	pytest --no-cov -x

test-cov:
	pytest --cov=apps --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

test-face:
	pytest apps/facerecognition/tests.py -v

test-watch:
	ptw

# Code quality
lint:
	flake8 apps/ project/ --max-line-length=100 --exclude=migrations

format:
	black apps/ project/ --line-length=100
	isort apps/ project/ --profile black

security-check:
	bandit -r apps/ project/ -ll

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

requirements:
	pip freeze > requirements.txt

# Check Django configuration
check-django:
	python manage.py check

# Create superuser
createsuperuser:
	python manage.py createsuperuser

# Show database info
dbshell:
	python manage.py dbshell

# Run shell
shell:
	python manage.py shell_plus
