"""
Symbolica Registry Module
========================

Agent and rule filtering utilities for organizing rules by context.

This module provides utilities for:
- Global pattern matching for rule selection
- Agent-specific rule filtering
- Rule registry management
"""

from __future__ import annotations

from .globmatch import filter_rules, _matches_any

# Convenience alias for pattern matching
def glob_match(pattern: str, names: list[str]) -> list[str]:
    """Match a single pattern against a list of names."""
    return [name for name in names if _matches_any(name, [pattern])]

__all__ = [
    "filter_rules",
    "glob_match",
] 