.PHONY: help setup dev test test-coverage test-fast test-watch lint format clean build docs

help:
	@echo "Emergent Learning Framework - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup           Install all dependencies (first-time setup)"
	@echo ""
	@echo "Development:"
	@echo "  make dev             Start all development servers (backend + frontend + dashboard)"
	@echo "  make dev-backend     Start just the backend API"
	@echo "  make dev-frontend    Start just the frontend dev server"
	@echo ""
	@echo "Testing:"
	@echo "  make test            Run all tests"
	@echo "  make test-coverage   Run tests with coverage report"
	@echo "  make test-fast       Run fast tests (skip slow ones)"
	@echo "  make test-watch      Run tests in watch mode (re-run on file changes)"
	@echo "  make test-backend    Run backend tests only"
	@echo "  make test-frontend   Run frontend tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint            Check code style and types"
	@echo "  make format          Auto-format code (Black + Prettier)"
	@echo "  make type-check      Run strict type checking"
	@echo ""
	@echo "Build & Docs:"
	@echo "  make build           Build frontend for production"
	@echo "  make docs            Generate documentation"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean           Remove build artifacts and cache"
	@echo ""

# Setup and installation
setup:
	@echo "Setting up Emergent Learning Framework..."
	@echo ""
	@echo "Step 1: Checking prerequisites..."
	@python -c "import sys; print(f'Python {sys.version}')"
	@command -v node >/dev/null 2>&1 && echo "Node.js found" || echo "Warning: Node.js not found"
	@echo ""
	@echo "Step 2: Installing Python dependencies..."
	@python -m pip install --upgrade pip setuptools
	@pip install -r requirements.txt
	@echo ""
	@echo "Step 3: Installing backend dependencies..."
	@cd apps/dashboard/backend && pip install -r requirements.txt
	@echo ""
	@echo "Step 4: Installing frontend dependencies..."
	@cd apps/dashboard/frontend && npm ci
	@echo ""
	@echo "Step 5: Verifying setup..."
	@python -m pytest tests/ --collect-only -q
	@echo ""
	@echo "✅ Setup complete! Run 'make dev' to start developing."

# Development servers
dev: dev-backend dev-frontend
	@echo "✅ All development servers running"
	@echo "  Backend:  http://localhost:8888"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Dashboard: http://localhost:3001"

dev-backend:
	@echo "Starting backend API server..."
	@cd apps/dashboard/backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8888

dev-frontend:
	@echo "Starting frontend dev server..."
	@cd apps/dashboard/frontend && npm run dev

# Testing
test:
	@pytest tests/ -v

test-coverage:
	@pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated: htmlcov/index.html"

test-fast:
	@pytest tests/ -v -m "not slow"

test-watch:
	@pytest-watch tests/ -- -v

test-backend:
	@cd apps/dashboard/backend && pytest tests/ -v

test-frontend:
	@cd apps/dashboard/frontend && npm run test

# Code quality
lint:
	@echo "Running linters..."
	@echo "  Python type checking (mypy)..."
	@mypy src/ --strict --no-implicit-reexport 2>/dev/null || echo "  (Fix type hints with errors above)"
	@echo "  Python linting (pylint)..."
	@pylint src/ --exit-zero 2>/dev/null || true
	@echo "  Shell script checking (shellcheck)..."
	@shellcheck scripts/*.sh 2>/dev/null || echo "  (Install shellcheck: brew install shellcheck)"
	@echo ""
	@echo "Tip: Fix issues with 'make format'"

format:
	@echo "Auto-formatting code..."
	@echo "  Black (Python)..."
	@black src/ tests/ scripts/ --quiet 2>/dev/null || echo "  (Install black: pip install black)"
	@echo "  Prettier (JavaScript/YAML)..."
	@cd apps/dashboard/frontend && npx prettier --write . 2>/dev/null || true
	@echo "✅ Formatting complete"

type-check:
	@echo "Strict type checking..."
	@mypy src/ tests/ scripts/ --strict --pretty --show-error-codes

# Building
build:
	@echo "Building frontend for production..."
	@cd apps/dashboard/frontend && npm run build
	@echo "✅ Build complete: apps/dashboard/frontend/dist/"

# Documentation
docs:
	@echo "Documentation files are in docs/ directory"
	@echo ""
	@echo "Key files:"
	@ls -lh docs/*.md | awk '{print "  " $$9 " (" $$5 ")"}'
	@echo ""
	@echo "To view:"
	@echo "  - ARCHITECTURE.md - System overview"
	@echo "  - TESTING.md - Testing guide"
	@echo "  - TROUBLESHOOTING.md - Common issues"

# Cleanup
clean:
	@echo "Cleaning up build artifacts and cache..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .coverage
	@cd apps/dashboard/frontend && rm -rf dist/ node_modules/.vite 2>/dev/null || true
	@echo "✅ Cleanup complete"
