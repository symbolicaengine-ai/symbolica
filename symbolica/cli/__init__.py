"""
Symbolica CLI Module
===================

Command-line interface for Symbolica rule engine operations.

Available commands:
- lint: Validate YAML rule files
- compile: Build rule packs from YAML
- run: Start REST API server  
- infer: Single inference execution
- test: Regression testing (stub)
- trace: Pretty-print trace files

Usage:
    $ symbolica --help
    $ symbolica compile --rules my_rules/ --output prod.rpack
    $ symbolica run --rpack prod.rpack --port 8080
"""

from __future__ import annotations

# The CLI is implemented as a single module for simplicity
from .__main__ import CLI, _main

__all__ = ["CLI", "_main", "main"]

# Alias for convenience
main = _main 