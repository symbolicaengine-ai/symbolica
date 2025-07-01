"""
symbolica.core.engine
====================

Main SymbolicaEngine class for deterministic reasoning.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Any, List, Optional, Union, AsyncIterator
import pathlib
import json
import tempfile

from .exceptions import RuleEngineError, RegistryNotFoundError
from .result import Result


class SymbolicaEngine:
    """Deterministic reasoning engine for AI applications."""
    
    def __init__(self, rules_path: Union[str, pathlib.Path]):
        """
        Initialize reasoning engine with all business rules.
        
        Args:
            rules_path: Path to rules directory or compiled .rpack file
        """
        self.rules_path = pathlib.Path(rules_path)
        self._pack_data = None
        self._reasoning_history: List[Result] = []
        self._load_rules()
    
    def _load_rules(self):
        """Load and compile all rules from directory or file."""
        if self.rules_path.suffix == '.rpack':
            # Load existing compiled rules
            if not self.rules_path.exists():
                raise FileNotFoundError(f"Rulepack not found: {self.rules_path}")
            self._pack_data = json.loads(self.rules_path.read_text())
        else:
            # Compile all rules recursively from directory
            if not self.rules_path.is_dir():
                raise RuleEngineError(f"Rules directory not found: {self.rules_path}")
            self._compile_rules()
        
        self._load_into_runtime()
    
    def _compile_rules(self):
        """Compile all rules recursively from directory."""
        try:
            from symbolica.compiler.lint import lint_folder
            from symbolica.compiler.packager import build_pack
            
            # Validate all rules
            errors = lint_folder(str(self.rules_path))
            if errors > 0:
                raise RuleEngineError(f"Rule validation failed with {errors} errors")
            
            # Compile to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.rpack', delete=False) as f:
                temp_path = f.name
            
            try:
                build_pack(str(self.rules_path), temp_path)
                self._pack_data = json.loads(pathlib.Path(temp_path).read_text())
            finally:
                pathlib.Path(temp_path).unlink()
                
        except Exception as e:
            if isinstance(e, RuleEngineError):
                raise
            raise RuleEngineError(f"Failed to compile rules: {e}") from e
    
    def _load_into_runtime(self):
        """Load compiled rules into runtime engine."""
        try:
            from symbolica.runtime.loader import load_pack
            
            # Use accessible directory instead of temp file
            cache_dir = pathlib.Path(".symbolica_cache")
            cache_dir.mkdir(exist_ok=True)
            
            # Create persistent rulepack file
            pack_path = cache_dir / "compiled_rules.rpack"
            pack_path.write_text(json.dumps(self._pack_data, ensure_ascii=False))
            
            load_pack(str(pack_path))
                
        except Exception as e:
            raise RuleEngineError(f"Failed to load rules into runtime: {e}") from e
    
    def _load_registry(self, rules_file: Union[str, pathlib.Path]) -> str:
        """Load registry file and return agent name for compatibility."""
        rules_path = pathlib.Path(rules_file)
        
        if not rules_path.exists():
            raise RegistryNotFoundError(f"Registry file not found: {rules_file}")
        
        try:
            if rules_path.suffix in ['.yaml', '.yml']:
                import yaml
                registry_data = yaml.safe_load(rules_path.read_text())
            elif rules_path.suffix == '.json':
                registry_data = json.loads(rules_path.read_text())
            else:
                raise RuleEngineError(f"Unsupported registry format: {rules_path.suffix}")
            
            # Extract agent name from registry for compatibility with existing runtime
            agent_name = registry_data.get("agent", rules_path.stem)
            return agent_name
            
        except Exception as e:
            if isinstance(e, (RegistryNotFoundError, RuleEngineError)):
                raise
            raise RuleEngineError(f"Failed to load registry {rules_file}: {e}") from e
    
    def infer(self, 
             facts: Dict[str, Any], 
             rules: Union[str, pathlib.Path],
             context: Optional[str] = None,
             trace_level: str = "verbose") -> Result:
        """
        Perform deterministic reasoning using specified rules.
        
        Args:
            facts: Facts to reason about
            rules: Path to registry file specifying which rules to use
            context: Context for this reasoning request
            trace_level: "compact", "verbose", or "debug"
            
        Returns:
            Result object with reasoning outcome and trace
        """
        # Load registry and get agent name for runtime compatibility
        agent_name = self._load_registry(rules)
        
        try:
            from symbolica.runtime.evaluator import infer as _infer
            verdict, trace = _infer(facts, agent_name, trace_level)
            
            result = Result(verdict, trace, context, str(rules))
            self._reasoning_history.append(result)
            
            return result
            
        except Exception as e:
            raise RuleEngineError(f"Reasoning failed with rules '{rules}': {e}") from e
    
    async def infer_async(self, 
                         facts: Dict[str, Any], 
                         rules: Union[str, pathlib.Path],
                         context: Optional[str] = None) -> Result:
        """Async reasoning for AI applications."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.infer, facts, rules, context)
    
    def infer_batch(self, 
                   batch: List[Dict[str, Any]], 
                   rules: Union[str, pathlib.Path],
                   context: Optional[str] = None) -> List[Result]:
        """Batch reasoning."""
        return [self.infer(facts, rules, context) for facts in batch]
    
    async def infer_stream(self, 
                          facts_stream: AsyncIterator[Dict[str, Any]], 
                          rules: Union[str, pathlib.Path],
                          context: Optional[str] = None) -> AsyncIterator[Result]:
        """Stream processing for real-time reasoning."""
        async for facts in facts_stream:
            yield await self.infer_async(facts, rules, context)
    
    def get_history(self, 
                   context: Optional[str] = None,
                   rules_file: Optional[str] = None) -> List[Result]:
        """Get reasoning history with optional filtering."""
        history = self._reasoning_history.copy()
        
        if context:
            history = [r for r in history if r.context == context]
        if rules_file:
            history = [r for r in history if r.rules_file == rules_file]
        
        return history
    
    @property
    def rules_count(self) -> int:
        """Total number of compiled rules."""
        return len(self._pack_data.get("rules", []))
    
    def save_pack(self, path: Union[str, pathlib.Path]) -> None:
        """Save compiled rules to .rpack file."""
        if self._pack_data is None:
            raise RuleEngineError("No rules loaded")
        pathlib.Path(path).write_text(json.dumps(self._pack_data, ensure_ascii=False))
    
    def __repr__(self) -> str:
        return f"SymbolicaEngine(rules={self.rules_count}, requests={len(self._reasoning_history)})" 