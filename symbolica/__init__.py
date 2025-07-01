"""
symbolica core package
Public API:
    - infer(facts: dict, agent: str, trace_level: str = "compact")
    - load_pack(path: str)
"""
from .runtime.loader import load_pack, get_runtime
from .runtime.evaluator import infer
__all__ = ["infer", "load_pack"]