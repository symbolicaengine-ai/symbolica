"""
symbolica.core.engine
====================

Main SymbolicaEngine class for deterministic reasoning.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Union, AsyncIterator
import pathlib
import json
import tempfile
from collections import defaultdict

from .exceptions import RuleEngineError, RegistryNotFoundError, ValidationError
from .result import Result

# Create logger for this module
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.start_time = time.time()
    
    def record_inference_time(self, duration_ms: float) -> None:
        """Record inference duration."""
        self.metrics['inference_times'].append(duration_ms)
        self.counters['total_inferences'] += 1
        
        # Log slow inferences
        if duration_ms > 1000:  # > 1 second
            logger.warning(f"Slow inference detected: {duration_ms:.2f}ms")
    
    def record_rule_count(self, count: int) -> None:
        """Record number of rules fired."""
        self.metrics['rules_fired'].append(count)
        self.counters['total_rules_fired'] += count
    
    def record_compilation_time(self, duration_ms: float) -> None:
        """Record compilation duration."""
        self.metrics['compilation_times'].append(duration_ms)
        self.counters['total_compilations'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        uptime = time.time() - self.start_time
        
        stats = {
            'uptime_seconds': uptime,
            'counters': dict(self.counters),
            'metrics': {}
        }
        
        # Calculate metric statistics
        for metric_name, values in self.metrics.items():
            if values:
                stats['metrics'][metric_name] = {
                    'count': len(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'p95': self._percentile(values, 95),
                    'p99': self._percentile(values, 99)
                }
        
        return stats
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def emit_metrics(self) -> None:
        """Emit metrics to logger."""
        stats = self.get_statistics()
        logger.info(f"Performance metrics: {json.dumps(stats, indent=2)}")


# Global performance monitor
_performance_monitor = PerformanceMonitor()


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
        self._engine = None
        
        logger.info(f"Initializing SymbolicaEngine with rules_path: {self.rules_path}")
        self._load_rules()
        logger.info(f"Engine initialized with {self.rules_count} rules")
    
    def _load_rules(self):
        """Load and compile all rules from directory or file."""
        logger.debug(f"Loading rules from: {self.rules_path}")
        
        if self.rules_path.suffix == '.rpack':
            # Load existing compiled rules
            logger.info(f"Loading pre-compiled rulepack: {self.rules_path}")
            if not self.rules_path.exists():
                raise FileNotFoundError(f"Rulepack not found: {self.rules_path}")
            self._pack_data = json.loads(self.rules_path.read_text())
        else:
            # Compile all rules recursively from directory
            if not self.rules_path.is_dir():
                raise RuleEngineError(f"Rules directory not found: {self.rules_path}")
            logger.info(f"Compiling rules from directory: {self.rules_path}")
            self._compile_rules()
        
        self._load_into_runtime()
    
    def _compile_rules(self):
        """Compile all rules recursively from directory."""
        compilation_start = time.time()
        
        try:
            # Import guard for compilation module
            try:
                from symbolica.compilation import compile_rules
            except ImportError as import_error:
                logger.error(f"Failed to import compilation module: {import_error}")
                raise RuleEngineError(
                    f"Compilation module not available: {import_error}. "
                    "Please check your installation or use pre-compiled .rpack files."
                ) from import_error
            
            logger.debug(f"Starting rule compilation for {self.rules_path}")
            
            # Compile rules using the new API
            compilation_result = compile_rules(self.rules_path, strict=False, optimize=True)
            if not compilation_result.success:
                logger.error(f"Rule compilation failed: {'; '.join(compilation_result.errors)}")
                raise RuleEngineError(f"Rule compilation failed: {'; '.join(compilation_result.errors)}")
            
            rule_count = len(compilation_result.rule_set.rules)
            compilation_time = (time.time() - compilation_start) * 1000
            
            logger.info(f"Successfully compiled {rule_count} rules in {compilation_time:.2f}ms")
            
            # Record performance metrics
            _performance_monitor.record_compilation_time(compilation_time)
            
            # Convert to pack format for compatibility
            self._pack_data = {
                "rules": [self._rule_to_dict(rule) for rule in compilation_result.rule_set.rules],
                "metadata": compilation_result.rule_set.metadata,
                "format_version": "1.0"
            }
                
        except Exception as e:
            logger.error(f"Failed to compile rules: {e}")
            if isinstance(e, RuleEngineError):
                raise
            raise RuleEngineError(f"Failed to compile rules: {e}") from e
    
    def _rule_to_dict(self, rule) -> Dict[str, Any]:
        """Convert Rule object to dictionary for compatibility."""
        return {
            "id": rule.id.value,
            "priority": rule.priority.value,
            "condition": {
                "expression": rule.condition.expression,
                "content_hash": rule.condition.content_hash,
                "referenced_fields": list(rule.condition.referenced_fields)
            },
            "actions": [
                {
                    "type": action.type,
                    "parameters": action.parameters
                }
                for action in rule.actions
            ],
            "tags": list(rule.tags),
            "written_fields": list(rule.written_fields)
        }
    
    def _load_into_runtime(self):
        """Load compiled rules into runtime engine."""
        try:
            # Import guard for engine module
            try:
                from symbolica.engine.inference import Engine
            except ImportError as import_error:
                logger.error(f"Failed to import engine module: {import_error}")
                raise RuleEngineError(
                    f"Engine module not available: {import_error}. "
                    "Please check your installation."
                ) from import_error
            
            # Create engine using directory/file
            if self.rules_path.is_dir():
                self._engine = Engine.from_directory(self.rules_path)
            else:
                self._engine = Engine.from_file(self.rules_path)
                
        except Exception as e:
            logger.error(f"Failed to load rules into runtime: {e}")
            if isinstance(e, RuleEngineError):
                raise
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
        # Input validation
        if not isinstance(facts, dict):
            raise ValidationError("Facts must be a dictionary")
        
        if trace_level not in ["compact", "verbose", "debug"]:
            raise ValidationError(f"trace_level must be 'compact', 'verbose', or 'debug'")
        
        logger.debug(f"Starting inference with {len(facts)} facts, trace_level: {trace_level}")
        
        try:
            # Use the new engine API for inference
            if self._engine is None:
                raise RuleEngineError("Engine not initialized. Check rules path.")
            
            # Perform reasoning
            execution_result = self._engine.reason(facts, trace=(trace_level == "debug"))
            
            # Record performance metrics
            _performance_monitor.record_inference_time(execution_result.execution_time_ms)
            _performance_monitor.record_rule_count(len(execution_result.fired_rules))
            
            # Log execution results
            logger.info(f"Inference completed in {execution_result.execution_time_ms:.2f}ms, "
                       f"fired {len(execution_result.fired_rules)} rules")
            
            # Convert to legacy Result format
            verdict = execution_result.verdict
            trace = {
                "fired": [rule_id.value for rule_id in execution_result.fired_rules],
                "execution_time_ms": execution_result.execution_time_ms,
                "success": execution_result.success
            }
            
            result = Result(verdict, trace, context, str(rules))
            self._reasoning_history.append(result)
            
            # Basic history bounds
            if len(self._reasoning_history) > 1000:
                logger.debug("Trimming reasoning history to prevent memory growth")
                self._reasoning_history = self._reasoning_history[-500:]  # Keep recent half
            
            return result
            
        except (RegistryNotFoundError, ValidationError):
            raise  # Re-raise expected errors
        except Exception as e:
            logger.error(f"Unexpected error during inference: {e}")
            raise RuleEngineError(f"Unexpected error during inference: {e}") from e
    
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
        if self._engine is None:
            return 0
        analysis = self._engine.get_analysis()
        return analysis.get("rule_count", 0)
    
    def save_pack(self, path: Union[str, pathlib.Path]) -> None:
        """Save compiled rules to .rpack file."""
        if self._pack_data is None:
            raise RuleEngineError("No rules loaded")
        pathlib.Path(path).write_text(json.dumps(self._pack_data, ensure_ascii=False))
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring."""
        stats = _performance_monitor.get_statistics()
        stats['engine_info'] = {
            'rules_count': self.rules_count,
            'reasoning_history_length': len(self._reasoning_history)
        }
        return stats
    
    def emit_performance_metrics(self) -> None:
        """Emit performance metrics to logs."""
        _performance_monitor.emit_metrics()
    
    def __repr__(self) -> str:
        return f"SymbolicaEngine(rules={self.rules_count}, requests={len(self._reasoning_history)})" 