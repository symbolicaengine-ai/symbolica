# Symbolica Test Suite Commands
# ============================

.PHONY: test test-critical test-unit test-integration test-extended test-performance test-fast test-ci test-all coverage clean

# Default: Run critical tests only
test: test-critical

# Test categories
test-critical:
	@echo "Running critical tests (must pass for basic functionality)..."
	pytest -m critical

test-unit:
	@echo "Running unit tests (fast, isolated)..."
	pytest -m unit

test-integration:
	@echo "Running integration tests (end-to-end workflows)..."
	pytest -m integration

test-extended:
	@echo "Running extended tests (edge cases and comprehensive coverage)..."
	pytest -m extended

test-performance:
	@echo "Running performance tests..."
	pytest -m performance

# Composite test sets
test-fast:
	@echo "Running fast tests (critical + unit, skip slow)..."
	pytest -m "critical or unit" -m "not slow"

test-ci:
	@echo "Running CI test suite (critical + integration)..."
	pytest -m "critical or integration"

test-all:
	@echo "Running all tests..."
	pytest

# Development shortcuts
test-dev:
	@echo "Running development test suite (skip extended and slow)..."
	pytest -m "not extended and not slow"

test-quick:
	@echo "Running quick smoke test (critical unit tests only)..."
	pytest -m "critical and unit"

# Coverage
coverage:
	@echo "Running tests with coverage report..."
	pytest --cov=symbolica --cov-report=html --cov-report=term-missing

coverage-critical:
	@echo "Running critical tests with coverage..."
	pytest -m critical --cov=symbolica --cov-report=term-missing

# Cleanup
clean:
	@echo "Cleaning test artifacts..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

# Help
help:
	@echo "Available test commands:"
	@echo "  test          - Run critical tests (default)"
	@echo "  test-critical - Run critical tests only"
	@echo "  test-unit     - Run unit tests only"  
	@echo "  test-integration - Run integration tests only"
	@echo "  test-extended - Run extended tests only"
	@echo "  test-performance - Run performance tests only"
	@echo ""
	@echo "  test-fast     - Run fast tests (critical + unit, skip slow)"
	@echo "  test-ci       - Run CI test suite (critical + integration)"
	@echo "  test-dev      - Run development tests (skip extended and slow)"
	@echo "  test-quick    - Run quick smoke test (critical unit only)"
	@echo "  test-all      - Run all tests"
	@echo ""
	@echo "  coverage      - Run tests with coverage"
	@echo "  clean         - Clean test artifacts" 