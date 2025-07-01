"""
symbolica core package
Public API:
    - infer(facts: dict, agent: str, trace_level: str = "compact")
    - load_pack(path: str)
"""
__version__ = "0.1.0"
from .runtime.loader import load_pack
from .runtime.evaluator import infer
__all__ = ["infer", "load_pack"]