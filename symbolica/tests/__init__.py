"""
Symbolica Test Suite
===================

Streamlined unit and integration tests for the Symbolica rule engine.

Test Structure:
- unit/: Unit tests for individual modules and components
- integration/: End-to-end integration tests
- fixtures/: Test data and shared fixtures

Pytest Markers:
- unit: Fast, isolated unit tests (<100ms)
- integration: End-to-end integration tests (<1s)
- critical: Essential tests that must pass for basic functionality
- extended: Extended test coverage for edge cases
- slow: Tests that take significant time (>1s)
- performance: Performance and benchmark tests

Usage Examples:
    # Run all tests
    pytest

    # Run only critical tests for CI/CD
    pytest -m critical

    # Run unit tests only
    pytest -m unit

    # Run integration tests
    pytest -m integration

    # Skip slow and extended tests for development
    pytest -m "not slow and not extended"

    # Run critical unit tests only
    pytest -m "critical and unit"

    # Run with coverage
    pytest --cov=symbolica

Test Categories:
- Critical tests: Core functionality that must work
- Extended tests: Edge cases and comprehensive coverage
- Performance tests: Benchmarks and scaling tests
"""

__version__ = "0.1.1" 