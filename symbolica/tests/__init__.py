"""
Symbolica Test Suite
===================

Comprehensive unit and integration tests for the Symbolica rule engine.

Test Structure:
- unit/: Unit tests for individual modules and components
- integration/: End-to-end integration tests
- fixtures/: Test data and shared fixtures
- benchmarks/: Performance and benchmark tests

Markers:
- unit: Unit tests (fast, isolated)
- integration: Integration tests (slower, system-level)
- benchmark: Performance benchmarks
- slow: Tests that take significant time

Usage:
    # Run all tests
    pytest

    # Run only unit tests
    pytest -m unit

    # Run integration tests
    pytest -m integration

    # Skip slow tests
    pytest -m "not slow"

    # Run with coverage
    pytest --cov=symbolica
"""

__version__ = "0.1.1" 