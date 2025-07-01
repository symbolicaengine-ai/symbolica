"""
Symbolica - Deterministic Rule Engine
=====================================

A high-performance, auditable rule engine that compiles YAML rules into 
hot-reloadable binary packs for sub-millisecond inference.

Basic Usage:
    >>> import symbolica
    >>> symbolica.load_pack("rules.rpack")
    >>> verdict, trace = symbolica.infer(
    ...     facts={"amount": 1500},
    ...     agent="FraudDetector"
    ... )

For advanced usage, see the compiler and runtime modules.
"""

from __future__ import annotations

import sys
from typing import Dict, Any, Tuple, Optional

# Version information
__version__ = "0.1.0"
__author__ = "Symbolica Contributors"
__license__ = "Apache 2.0"

# Minimum Python version check
if sys.version_info < (3, 8):
    raise RuntimeError("Symbolica requires Python 3.8 or higher")


# ═══════════════════════════════════════════════════════════════════════════
# Core Exceptions
# ═══════════════════════════════════════════════════════════════════════════

class SymbolicaError(Exception):
    """Base exception for all Symbolica errors."""
    pass


class RulepackError(SymbolicaError):
    """Errors related to rulepack loading/validation."""
    pass


class CompilationError(SymbolicaError):
    """Errors during rule compilation."""
    pass


class EvaluationError(SymbolicaError):
    """Errors during rule evaluation."""
    pass


class ConfigurationError(SymbolicaError):
    """Errors in configuration or setup."""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# Core Public API
# ═══════════════════════════════════════════════════════════════════════════

def load_pack(path: str) -> None:
    """
    Load a compiled rulepack file.
    
    Args:
        path: Path to the .rpack file
        
    Raises:
        RulepackError: If the rulepack cannot be loaded
        FileNotFoundError: If the file doesn't exist
        
    Example:
        >>> symbolica.load_pack("fraud_rules.rpack")
    """
    try:
        from .runtime.loader import load_pack as _load_pack
        return _load_pack(path)
    except FileNotFoundError:
        raise
    except Exception as e:
        raise RulepackError(f"Failed to load rulepack '{path}': {e}") from e


def infer(
    facts: Dict[str, Any], 
    agent: str,
    trace_level: str = "compact"
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Run rule inference on the provided facts.
    
    Args:
        facts: Dictionary of facts to evaluate against rules
        agent: Agent name that determines which rules to use
        trace_level: Level of trace detail ("compact", "verbose", "debug")
        
    Returns:
        Tuple of (verdict, trace) dictionaries
        
    Raises:
        EvaluationError: If inference fails
        KeyError: If the agent is unknown
        
    Example:
        >>> verdict, trace = symbolica.infer(
        ...     facts={"transaction_amount": 1500, "country": "US"},
        ...     agent="FraudDetector",
        ...     trace_level="verbose"
        ... )
        >>> print(verdict["decision_status"])
    """
    try:
        from .runtime.evaluator import infer as _infer
        return _infer(facts, agent, trace_level)
    except KeyError as e:
        if "agents" in str(e):
            raise KeyError(f"Unknown agent '{agent}'. Check your rulepack configuration.") from e
        raise
    except Exception as e:
        raise EvaluationError(f"Inference failed: {e}") from e


def get_pack_info() -> Dict[str, Any]:
    """
    Get information about the currently loaded rulepack.
    
    Returns:
        Dictionary with pack metadata (version, agents, rule count, etc.)
        
    Raises:
        RulepackError: If no rulepack is loaded
    """
    try:
        from .runtime.loader import get_pack
        pack = get_pack()
        return {
            "version": pack.header.get("version"),
            "built": pack.header.get("built"), 
            "agents": list(pack.header.get("agents", {}).keys()),
            "rule_count": len(pack.rules),
            "status_precedence": pack.header.get("status_precedence", [])
        }
    except RuntimeError as e:
        raise RulepackError(str(e)) from e


# ═══════════════════════════════════════════════════════════════════════════
# Submodule Lazy Loading
# ═══════════════════════════════════════════════════════════════════════════

def __getattr__(name: str) -> Any:
    """Lazy loading of submodules."""
    if name == "compiler":
        from . import compiler
        return compiler
    elif name == "runtime":
        from . import runtime  
        return runtime
    elif name == "cli":
        from . import cli
        return cli
    elif name == "registry":
        from . import registry
        return registry
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# ═══════════════════════════════════════════════════════════════════════════
# Public API Exports
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    # Core functions
    "infer",
    "load_pack", 
    "get_pack_info",
    
    # Exceptions
    "SymbolicaError",
    "RulepackError", 
    "CompilationError",
    "EvaluationError",
    "ConfigurationError",
    
    # Version info
    "__version__",
    "__author__",
    "__license__",
]


# ═══════════════════════════════════════════════════════════════════════════
# Package Level Configuration
# ═══════════════════════════════════════════════════════════════════════════

# Default configuration that can be modified by users
config = {
    "default_trace_level": "compact",
    "cache_compiled_rules": True,
    "hot_reload_check_interval": 1.0,  # seconds
    "max_rule_execution_time": 10.0,   # seconds
}


def configure(**kwargs) -> None:
    """
    Update global Symbolica configuration.
    
    Args:
        **kwargs: Configuration options to update
        
    Example:
        >>> symbolica.configure(
        ...     default_trace_level="verbose",
        ...     hot_reload_check_interval=0.5
        ... )
    """
    for key, value in kwargs.items():
        if key not in config:
            raise ConfigurationError(f"Unknown configuration option: {key}")
        config[key] = value


def get_config() -> Dict[str, Any]:
    """Get current configuration."""
    return config.copy()


# Add configuration functions to exports
__all__.extend(["configure", "get_config", "config"])