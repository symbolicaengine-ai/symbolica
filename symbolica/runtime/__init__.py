"""
Symbolica Runtime Module
========================

High-performance rule execution engine with memory-mapped rule loading,
sub-millisecond inference, and comprehensive tracing.

This module contains:
- Rule pack loader with hot-reload capability
- Forward-chaining rule evaluator  
- Execution tracing system
- Optional REST API server
"""

from __future__ import annotations

from typing import Dict, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .loader import RulePack

# Core runtime functions
from .loader import load_pack, get_pack
from .evaluator import infer
from .trace import TraceBuilder

# Optional REST API (may not be available if FastAPI not installed)
try:
    from .api import app as rest_app
    HAS_REST_API = True
except ImportError:
    rest_app = None
    HAS_REST_API = False

__all__ = [
    # Core functions
    "load_pack",
    "get_pack", 
    "infer",
    
    # Tracing
    "TraceBuilder",
    
    # REST API (if available)
    "rest_app",
    "HAS_REST_API",
]


def get_runtime_info() -> Dict[str, Any]:
    """Get information about the runtime environment."""
    try:
        pack = get_pack()
        pack_loaded = True
        pack_info = {
            "version": pack.header.get("version"),
            "rule_count": len(pack.rules),
            "agents": list(pack.header.get("agents", {}).keys())
        }
    except RuntimeError:
        pack_loaded = False
        pack_info = {}
    
    return {
        "pack_loaded": pack_loaded,
        "pack_info": pack_info,
        "rest_api_available": HAS_REST_API,
    }


__all__.append("get_runtime_info") 