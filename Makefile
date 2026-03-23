.PHONY: help install install-dev clean test test-validation test-transformations test-all test-local lint format format-check type-check generate-examples ci ci-check validate-examples \
        build rebuild up down restart logs shell docker-clean dist release docs info

# ── Variables ─────────────────────────────────────────────────────────────────

PYTHON := python3
PIP := pip3
VENV := .venv

COMPOSE   = docker compose -f docker/docker-compose.yml
API_PORT  ?= 8080
LSP_PORT  ?= 2087
API_KEY   ?=
LOG_LEVEL ?= INFO

export API_PORT LSP_PORT API_KEY LOG_LEVEL

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "DeMoL - Device Modeling Language"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-25s %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# Installation & Setup
# ============================================================================

venv: ## Create virtual environment
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "✓ Virtual environment created"
	@echo "Activate with: source $(VENV)/bin/activate"

install: venv ## Install demol in production mode
	@echo "Installing demol..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	@echo "✓ Installation complete"

install-dev: venv ## Install demol in development mode with dev dependencies
	@echo "Installing demol (development mode)..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	$(PIP) install pytest pytest-cov black flake8 mypy
	@echo "✓ Development installation complete"

clean: ## Clean build artifacts and cache files
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf rpi_out/
	rm -rf tests/output/
	@echo "✓ Cleanup complete"

# ============================================================================
# Testing
# ============================================================================

test: ## Run all pytest tests
	@echo "Running pytest tests..."
	$(PYTHON) -m pytest tests/ -v
	@echo "✓ Tests complete"

test-validation: ## Run validation tests
	@echo "Running validation tests..."
	$(PYTHON) scripts/test_validation.py
	@echo "✓ Validation tests complete"

test-transformations: ## Run transformation tests
	@echo "Running transformation tests..."
	$(PYTHON) scripts/test_transformations.py
	@echo "✓ Transformation tests complete"

test-local: test test-validation test-transformations ## Run all tests locally (pytest + validation + transformations)
	@echo "✓ All local tests complete"

test-all: ## Run all tests in a Docker container
	@echo "Building test container..."
	docker build -t demol-tests -f docker/Dockerfile.tests .
	@echo "Running tests in container..."
	docker run --rm demol-tests

test-cov: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest tests/ --cov=demol --cov-report=html --cov-report=term
	@echo "✓ Coverage report generated in htmlcov/"

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run linting checks (flake8)
	@echo "Running linting checks..."
	$(PYTHON) -m flake8 demol/ --max-line-length=120 --exclude=__pycache__,.venv,demol/lang/semantics.py --extend-ignore=E203,E501
	@echo "✓ Linting complete"

format: ## Format code with black
	@echo "Formatting code with black..."
	$(PYTHON) -m black demol/ tests/ scripts/ --line-length=120
	@echo "✓ Code formatting complete"

format-check: ## Check formatting without modifying files
	@echo "Checking code formatting..."
	$(PYTHON) -m black --check demol/ tests/ scripts/ --line-length=120
	@echo "✓ Formatting check passed"

type-check: ## Run type checking with mypy
	@echo "Running type checks..."
	$(PYTHON) -m mypy demol/ --ignore-missing-imports
	@echo "✓ Type checking complete"

# ============================================================================
# Code Generation
# ============================================================================

generate-examples: ## Generate code for all RPI examples
	@echo "Generating RPI examples..."
	$(PYTHON) scripts/generate_rpi_examples.py
	@echo "✓ Code generation complete"

validate-examples: ## Validate all example models
	@echo "Validating example models..."
	@for file in examples/rpi/*.dev examples/esp/*.dev; do \
		[ -f "$$file" ] || continue; \
		echo "Validating $$file..."; \
		$(PYTHON) -m demol.cli.cli validate "$$file" || exit 1; \
	done
	@echo "✓ All examples validated"

# ============================================================================
# Docker (tx-lsp — LSP :2087, REST API :8080)
# ============================================================================

build: ## Build Docker image
	$(COMPOSE) build

rebuild: ## Build Docker image (no cache)
	$(COMPOSE) build --no-cache

up: ## Start services (detached)
	$(COMPOSE) up -d

down: ## Stop services
	$(COMPOSE) down

restart: ## Restart services
	$(COMPOSE) restart

logs: ## Tail service logs
	$(COMPOSE) logs -f

shell: ## Open a shell in the running container
	$(COMPOSE) exec demol /bin/bash

docker-clean: ## Stop services and remove images + volumes
	$(COMPOSE) down --rmi all --volumes

# ============================================================================
# Development Utilities
# ============================================================================

dev-setup: install-dev ## Complete development setup (install + pre-commit hooks)
	@echo "Setting up development environment..."
	@echo "✓ Development environment ready"
	@echo "Run 'source $(VENV)/bin/activate' to activate the virtual environment"

check: lint type-check test-local ## Run all quality checks locally (lint + type-check + tests)
	@echo "✓ All checks passed"

ci-check: format-check lint type-check test validate-examples ## Full CI pipeline (format + lint + type-check + tests + examples)
	@echo "✓ CI pipeline complete"

ci: ## Run full CI pipeline in a Docker container
	@echo "Building CI container..."
	docker build -t demol-ci -f docker/Dockerfile.tests .
	@echo "Running full CI pipeline in container..."
	docker run --rm demol-ci
	@echo "✓ CI pipeline complete"

# ============================================================================
# Documentation
# ============================================================================

docs: ## Generate documentation (placeholder)
	@echo "Documentation generation not yet implemented"

# ============================================================================
# Release
# ============================================================================

dist: clean ## Build distribution packages (sdist + wheel)
	@echo "Building distribution packages..."
	$(PYTHON) setup.py sdist bdist_wheel
	@echo "✓ Build complete - packages in dist/"

release: dist ## Build and prepare for release
	@echo "Preparing release..."
	@echo "Run 'twine upload dist/*' to upload to PyPI"

# ============================================================================
# Info
# ============================================================================

info: ## Show project information
	@echo "DeMoL Project Information"
	@echo ""
	@echo "Version:       0.0.1"
	@echo "Python:        $$($(PYTHON) --version 2>&1)"
	@echo "Venv:          $(VENV)"
	@echo "LSP Port:      $(LSP_PORT)"
	@echo "API Port:      $(API_PORT)"
	@echo ""
	@echo "Project Structure:"
	@echo "  demol/           - Core library"
	@echo "  tests/           - Test suite"
	@echo "  scripts/         - Utility scripts"
	@echo "  examples/        - Example models"
	@echo "  templates/       - Code generation templates"
	@echo ""
