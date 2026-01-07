.PHONY: help install install-dev clean test test-validation test-transformations test-all lint format docker-build docker-run docker-clean generate-examples

# Variables
PYTHON := python3
PIP := pip3
VENV := .venv
VENV_BIN := $(VENV)/bin
DOCKER_IMAGE := demol
DOCKER_TAG := latest
DOCKER_IMAGE_FULL := $(DOCKER_IMAGE):$(DOCKER_TAG)

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)DeMoL - Device Modeling Language$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# Installation & Setup
# ============================================================================

venv: ## Create virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)✓ Virtual environment created$(NC)"
	@echo "$(YELLOW)Activate with: source $(VENV_BIN)/activate$(NC)"

install: venv ## Install demol in production mode
	@echo "$(BLUE)Installing demol...$(NC)"
	$(VENV_BIN)/$(PIP) install --upgrade pip
	$(VENV_BIN)/$(PIP) install -r requirements.txt
	$(VENV_BIN)/$(PIP) install -e .
	@echo "$(GREEN)✓ Installation complete$(NC)"

install-dev: venv ## Install demol in development mode with dev dependencies
	@echo "$(BLUE)Installing demol (development mode)...$(NC)"
	$(VENV_BIN)/$(PIP) install --upgrade pip
	$(VENV_BIN)/$(PIP) install -r requirements.txt
	$(VENV_BIN)/$(PIP) install -e .
	$(VENV_BIN)/$(PIP) install pytest pytest-cov black flake8 mypy
	@echo "$(GREEN)✓ Development installation complete$(NC)"

clean: ## Clean build artifacts and cache files
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
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
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

# ============================================================================
# Testing
# ============================================================================

test: ## Run all pytest tests
	@echo "$(BLUE)Running pytest tests...$(NC)"
	$(VENV_BIN)/pytest tests/ -v
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-validation: ## Run validation tests
	@echo "$(BLUE)Running validation tests...$(NC)"
	$(VENV_BIN)/$(PYTHON) scripts/test_validation.py
	@echo "$(GREEN)✓ Validation tests complete$(NC)"

test-transformations: ## Run transformation tests
	@echo "$(BLUE)Running transformation tests...$(NC)"
	$(VENV_BIN)/$(PYTHON) scripts/test_transformations.py
	@echo "$(GREEN)✓ Transformation tests complete$(NC)"

test-all: test test-validation test-transformations ## Run all tests (pytest + validation + transformations)
	@echo "$(GREEN)✓ All tests complete$(NC)"

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(VENV_BIN)/pytest tests/ --cov=demol --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run linting checks (flake8)
	@echo "$(BLUE)Running linting checks...$(NC)"
	$(VENV_BIN)/flake8 demol/ --max-line-length=120 --exclude=__pycache__,.venv
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code with black
	@echo "$(BLUE)Formatting code with black...$(NC)"
	$(VENV_BIN)/black demol/ tests/ scripts/ --line-length=120
	@echo "$(GREEN)✓ Code formatting complete$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	$(VENV_BIN)/mypy demol/ --ignore-missing-imports
	@echo "$(GREEN)✓ Type checking complete$(NC)"

# ============================================================================
# Code Generation
# ============================================================================

generate-examples: ## Generate code for all RPI examples
	@echo "$(BLUE)Generating RPI examples...$(NC)"
	$(VENV_BIN)/$(PYTHON) scripts/generate_rpi_examples.py
	@echo "$(GREEN)✓ Code generation complete$(NC)"

validate-examples: ## Validate all example models
	@echo "$(BLUE)Validating example models...$(NC)"
	@for file in examples/rpi/*.dev; do \
		echo "Validating $$file..."; \
		$(VENV_BIN)/$(PYTHON) -m demol.cli.cli validate "$$file" || exit 1; \
	done
	@echo "$(GREEN)✓ All examples validated$(NC)"

# ============================================================================
# Docker
# ============================================================================

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image $(DOCKER_IMAGE_FULL)...$(NC)"
	docker build -t $(DOCKER_IMAGE_FULL) .
	@echo "$(GREEN)✓ Docker image built: $(DOCKER_IMAGE_FULL)$(NC)"

docker-run: ## Run Docker container
	@echo "$(BLUE)Running Docker container...$(NC)"
	docker run -it --rm \
		-v $(PWD):/workspace \
		-w /workspace \
		$(DOCKER_IMAGE_FULL) \
		/bin/bash
	@echo "$(GREEN)✓ Docker container stopped$(NC)"

docker-test: ## Run tests in Docker container
	@echo "$(BLUE)Running tests in Docker...$(NC)"
	docker run --rm \
		-v $(PWD):/workspace \
		-w /workspace \
		$(DOCKER_IMAGE_FULL) \
		make test-all
	@echo "$(GREEN)✓ Docker tests complete$(NC)"

docker-clean: ## Remove Docker images
	@echo "$(BLUE)Removing Docker images...$(NC)"
	docker rmi $(DOCKER_IMAGE_FULL) 2>/dev/null || true
	@echo "$(GREEN)✓ Docker cleanup complete$(NC)"

docker-shell: ## Open shell in Docker container
	@echo "$(BLUE)Opening shell in Docker container...$(NC)"
	docker run -it --rm \
		-v $(PWD):/workspace \
		-w /workspace \
		$(DOCKER_IMAGE_FULL) \
		/bin/bash

# ============================================================================
# Development Utilities
# ============================================================================

dev-setup: install-dev ## Complete development setup (install + pre-commit hooks)
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@echo "$(GREEN)✓ Development environment ready$(NC)"
	@echo "$(YELLOW)Run 'source $(VENV_BIN)/activate' to activate the virtual environment$(NC)"

check: lint type-check test-all ## Run all quality checks (lint + type-check + tests)
	@echo "$(GREEN)✓ All checks passed$(NC)"

ci: clean install test-all ## CI pipeline (clean + install + test)
	@echo "$(GREEN)✓ CI pipeline complete$(NC)"

# ============================================================================
# Documentation
# ============================================================================

docs: ## Generate documentation (placeholder)
	@echo "$(YELLOW)Documentation generation not yet implemented$(NC)"

# ============================================================================
# Release
# ============================================================================

build: clean ## Build distribution packages
	@echo "$(BLUE)Building distribution packages...$(NC)"
	$(VENV_BIN)/$(PYTHON) setup.py sdist bdist_wheel
	@echo "$(GREEN)✓ Build complete - packages in dist/$(NC)"

release: build ## Build and prepare for release
	@echo "$(BLUE)Preparing release...$(NC)"
	@echo "$(YELLOW)Run 'twine upload dist/*' to upload to PyPI$(NC)"

# ============================================================================
# Info
# ============================================================================

info: ## Show project information
	@echo "$(BLUE)DeMoL Project Information$(NC)"
	@echo ""
	@echo "$(GREEN)Version:$(NC)       0.0.1"
	@echo "$(GREEN)Python:$(NC)        $$($(PYTHON) --version 2>&1)"
	@echo "$(GREEN)Venv:$(NC)          $(VENV)"
	@echo "$(GREEN)Docker Image:$(NC)  $(DOCKER_IMAGE_FULL)"
	@echo ""
	@echo "$(GREEN)Project Structure:$(NC)"
	@echo "  demol/           - Core library"
	@echo "  tests/           - Test suite"
	@echo "  scripts/         - Utility scripts"
	@echo "  examples/        - Example models"
	@echo "  templates/       - Code generation templates"
	@echo ""
