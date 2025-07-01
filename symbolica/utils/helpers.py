"""
symbolica.utils.helpers
======================

Utility functions for Symbolica.
"""

from __future__ import annotations

from typing import Dict, Any, Union, Optional
import pathlib

from ..core.engine import SymbolicaEngine
from ..core.result import Result


def quick_infer(facts: Dict[str, Any], 
               rules: Union[str, pathlib.Path],
               rules_path: Union[str, pathlib.Path],
               context: Optional[str] = None) -> Result:
    """Quick reasoning without creating engine object."""
    engine = SymbolicaEngine(rules_path)
    return engine.infer(facts, rules, context)


def compile_rules(rules_dir: Union[str, pathlib.Path], 
                 output_path: Union[str, pathlib.Path]) -> None:
    """Compile rules directory to .rpack file."""
    engine = SymbolicaEngine(rules_dir)
    engine.save_pack(output_path) 