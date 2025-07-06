"""
Symbolica Inference Engine
==========================

Main engine for AI agents with comprehensive rule processing capabilities.

Features:
- YAML rule compilation
- Advanced expression evaluation
- DAG-based parallel execution
- Multiple execution strategies
- Performance optimization
"""

import time
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from ..core import (
    Facts, ExecutionResult, RuleSet, Rule,
    facts, rule_id, priority, condition, action_set,
    SymbolicaError, ValidationError
)
from ..compilation import compile_rules, RuleCompiler, CompilationResult
from .._internal.evaluator import create_evaluator
from .._internal.executor import create_executor
from .._internal.strategies import create_optimal_strategy
from .._internal.dag import create_dag_strategy, ConflictResolution


class Engine:
    """
    Main inference engine for AI agents.
    
    Features:
    - Compiles YAML rules on-the-fly
    - Advanced expression evaluation
    - Multiple execution strategies
    - Performance optimization
    - Clean API for AI frameworks
    """
    
    def __init__(self, execution_strategy: str = "auto", 
                 max_workers: int = 4,
                 conflict_resolution: str = "priority"):
        """
        Initialize inference engine.
        
        Args:
            execution_strategy: "linear", "dag", "optimized", or "auto"
            max_workers: Maximum parallel workers for DAG execution
            conflict_resolution: "priority", "first_wins", "last_wins", or "error"
        """
        self.execution_strategy = execution_strategy
        self.max_workers = max_workers
        self.conflict_resolution = ConflictResolution(conflict_resolution)
        
        # Core components
        self._evaluator = create_evaluator()
        self._executor = create_executor()
        self._strategy = None
        self._ruleset: Optional[RuleSet] = None
        
        # Compilation cache
        self._compilation_cache: Dict[str, RuleSet] = {}
    
    @classmethod
    def from_yaml(cls, yaml_content: str, **kwargs) -> 'Engine':
        """Create engine from YAML rules string."""
        engine = cls(**kwargs)
        engine.load_yaml(yaml_content)
        return engine
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path], **kwargs) -> 'Engine':
        """Create engine from YAML file."""
        engine = cls(**kwargs)
        engine.load_file(file_path)
        return engine
    
    @classmethod
    def from_directory(cls, directory: Union[str, Path], **kwargs) -> 'Engine':
        """Create engine from directory of YAML files."""
        engine = cls(**kwargs)
        engine.load_directory(directory)
        return engine
    
    @classmethod
    def from_rules(cls, rules: List[Rule], **kwargs) -> 'Engine':
        """Create engine from pre-compiled rules."""
        engine = cls(**kwargs)
        engine.load_rules(rules)
        return engine
    
    def load_yaml(self, yaml_content: str) -> None:
        """Load rules from YAML string."""
        cache_key = f"yaml:{hash(yaml_content)}"
        
        if cache_key not in self._compilation_cache:
            result = compile_rules(yaml_content, strict=False, optimize=True)
            if not result.success:
                raise ValidationError(f"Compilation failed: {'; '.join(result.errors)}")
            self._compilation_cache[cache_key] = result.rule_set
        
        self._ruleset = self._compilation_cache[cache_key]
        self._strategy = self._select_strategy(self._ruleset.rules)
    
    def load_file(self, file_path: Union[str, Path]) -> None:
        """Load rules from YAML file."""
        path = Path(file_path)
        cache_key = f"file:{path}:{path.stat().st_mtime}"
        
        if cache_key not in self._compilation_cache:
            result = compile_rules(path, strict=False, optimize=True)
            if not result.success:
                raise ValidationError(f"Compilation failed: {'; '.join(result.errors)}")
            self._compilation_cache[cache_key] = result.rule_set
        
        self._ruleset = self._compilation_cache[cache_key]
        self._strategy = self._select_strategy(self._ruleset.rules)
    
    def load_directory(self, directory: Union[str, Path]) -> None:
        """Load rules from directory of YAML files."""
        dir_path = Path(directory)
        
        # Create cache key based on all YAML files and their modification times
        yaml_files = list(dir_path.rglob('*.yaml')) + list(dir_path.rglob('*.yml'))
        file_info = [(f, f.stat().st_mtime) for f in yaml_files if f.exists()]
        cache_key = f"dir:{dir_path}:{hash(tuple(file_info))}"
        
        if cache_key not in self._compilation_cache:
            result = compile_rules(dir_path, strict=False, optimize=True)
            if not result.success:
                raise ValidationError(f"Compilation failed: {'; '.join(result.errors)}")
            self._compilation_cache[cache_key] = result.rule_set
        
        self._ruleset = self._compilation_cache[cache_key]
        self._strategy = self._select_strategy(self._ruleset.rules)
    
    def load_rules(self, rules: List[Rule]) -> None:
        """Load pre-compiled rules."""
        self._ruleset = RuleSet(rules)
        self._strategy = self._select_strategy(rules)
    
    def reason(self, 
               facts_data: Dict[str, Any],
               trace: bool = False) -> ExecutionResult:
        """
        Perform reasoning - main method for AI agents.
        
        Args:
            facts_data: Input facts to reason about
            trace: Whether to include execution trace
            
        Returns:
            ExecutionResult with verdict and optional trace
        """
        if not isinstance(facts_data, dict):
            raise ValidationError("Facts must be a dictionary")
        
        if self._ruleset is None:
            raise SymbolicaError("No rules loaded. Call load_yaml(), load_file(), or load_rules() first")
        
        try:
            # Create immutable facts
            input_facts = facts(facts_data)
            
            # Execute using selected strategy
            result = self._strategy.execute(
                rules=self._ruleset.rules,
                facts=input_facts,
                evaluator=self._evaluator,
                action_executor=self._executor
            )
            
            return result
            
        except Exception as e:
            if isinstance(e, SymbolicaError):
                raise
            raise SymbolicaError(f"Reasoning failed: {e}") from e
    
    def test_condition(self, expression: str, facts_data: Dict[str, Any]) -> bool:
        """
        Test a condition against facts (useful for debugging).
        
        Args:
            expression: Condition expression to test
            facts_data: Facts to test against
            
        Returns:
            True if condition is satisfied
        """
        input_facts = facts(facts_data)
        from ..core import ExecutionContext, TraceLevel
        
        context = ExecutionContext(
            original_facts=input_facts,
            enriched_facts={},
            fired_rules=[],
            trace_level=TraceLevel.NONE
        )
        
        test_condition = condition(expression)
        return self._evaluator.evaluate(test_condition, context)
    
    def get_analysis(self) -> Dict[str, Any]:
        """Get analysis of loaded rules."""
        if self._ruleset is None:
            raise SymbolicaError("No rules loaded")
        
        analysis = {
            'rule_count': self._ruleset.rule_count,
            'execution_strategy': self._strategy.name() if self._strategy else 'none',
            'metadata': self._ruleset.metadata
        }
        
        # Add DAG analysis if using DAG strategy
        if hasattr(self._strategy, 'get_dag_info'):
            analysis['dag_analysis'] = self._strategy.get_dag_info(
                self._ruleset.rules, self._evaluator
            )
        
        return analysis
    
    def _select_strategy(self, rules: List[Rule]):
        """Select optimal execution strategy."""
        if self.execution_strategy == "linear":
            from .._internal.strategies import LinearExecutionStrategy
            return LinearExecutionStrategy()
        
        elif self.execution_strategy == "dag":
            return create_dag_strategy(self.max_workers, self.conflict_resolution)
        
        elif self.execution_strategy == "optimized":
            from .._internal.strategies import OptimizedLinearStrategy
            return OptimizedLinearStrategy()
        
        elif self.execution_strategy == "auto":
            # Auto-select based on rule count and complexity
            rule_count = len(rules)
            
            if rule_count <= 5:
                from .._internal.strategies import LinearExecutionStrategy
                return LinearExecutionStrategy()
            elif rule_count <= 20:
                from .._internal.strategies import OptimizedLinearStrategy
                return OptimizedLinearStrategy()
            else:
                return create_dag_strategy(self.max_workers, self.conflict_resolution)
        
        else:
            raise ValueError(f"Unknown execution strategy: {self.execution_strategy}")


# Convenience functions for quick usage
def quick_reason(yaml_rules: str, facts_data: Dict[str, Any], **kwargs) -> ExecutionResult:
    """Quick reasoning without creating engine object."""
    engine = Engine.from_yaml(yaml_rules, **kwargs)
    return engine.reason(facts_data)


def from_yaml(yaml_content: str, **kwargs) -> Engine:
    """Create engine from YAML - convenience function."""
    return Engine.from_yaml(yaml_content, **kwargs)


def create_simple_rule(rule_id: str, condition: str, **actions) -> Rule:
    """
    Create a simple rule for programmatic use.
    
    Args:
        rule_id: Unique rule identifier
        condition: Condition expression
        **actions: Actions to execute (will be converted to 'set' action)
    
    Returns:
        Rule object
    """
    return Rule(
        id=rule_id(rule_id),
        priority=priority(50),
        condition=condition(condition),
        actions=[action_set(**actions)] if actions else [],
        tags=frozenset()
    )


# Example usage and testing
def create_example_engine() -> Engine:
    """Create example engine for testing."""
    yaml_rules = """
rules:
  - id: high_value_customer
    priority: 100
    if: "customer_value > 1000 and account_status == 'active'"
    then:
      set:
        tier: premium
        discount: 0.15
        
  - id: loyalty_bonus
    priority: 90
    if: "tier == 'premium' and years_active >= 5"
    then:
      set:
        loyalty_bonus: true
        additional_discount: 0.05
        
  - id: risk_assessment
    priority: 80
    if: "payment_history_score < 70 or credit_rating == 'poor'"
    then:
      set:
        risk_level: high
        requires_approval: true
    """
    
    return Engine.from_yaml(yaml_rules, execution_strategy="dag") 