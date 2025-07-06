"""
Symbolica Engine
===============

Main inference engine for AI agents.
"""

from .inference import Engine, quick_reason, create_simple_rule

__all__ = [
    "Engine",
    "quick_reason", 
    "create_simple_rule",
] 