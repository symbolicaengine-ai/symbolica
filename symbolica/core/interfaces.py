"""
Symbolica Core Interfaces
=========================

Key extension points for the rule engine.
Only interfaces where pluggability is genuinely needed.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, FrozenSet, Optional
from .models import Rule, Facts, ExecutionContext, ExecutionResult, Condition


class ConditionEvaluator(ABC):
    """Evaluates rule conditions against facts."""
    
    @abstractmethod
    def evaluate(self, condition: Condition, context: ExecutionContext) -> bool:
        """
        Evaluate condition against execution context.
        
        Args:
            condition: The condition to evaluate
            context: Current execution context with facts
            
        Returns:
            True if condition is satisfied
        """
        pass
    
    @abstractmethod  
    def extract_fields(self, condition: Condition) -> FrozenSet[str]:
        """
        Extract field names referenced by the condition.
        
        Args:
            condition: The condition to analyze
            
        Returns:
            Set of field names referenced
        """
        pass


class ActionExecutor(ABC):
    """Executes rule actions."""
    
    @abstractmethod
    def execute(self, actions: List[Any], context: ExecutionContext) -> None:
        """
        Execute actions, modifying the context.
        
        Args:
            actions: List of actions to execute
            context: Execution context to modify
        """
        pass
    
    @abstractmethod
    def supported_action_types(self) -> List[str]:
        """
        Get list of supported action types.
        
        Returns:
            List of action type names this executor supports
        """
        pass


class ExecutionStrategy(ABC):
    """Strategy for executing rules."""
    
    @abstractmethod
    def execute(self, rules: List[Rule], facts: Facts, 
                evaluator: ConditionEvaluator, 
                action_executor: ActionExecutor) -> ExecutionResult:
        """
        Execute rules using this strategy.
        
        Args:
            rules: Rules to execute
            facts: Input facts
            evaluator: Condition evaluator
            action_executor: Action executor
            
        Returns:
            Execution result
        """
        pass
    
    @abstractmethod
    def name(self) -> str:
        """Strategy name for debugging."""
        pass


class Cache(ABC):
    """Caching interface for performance."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set cached value."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Get cache size."""
        pass


class Tracer(ABC):
    """Execution tracing for debugging."""
    
    @abstractmethod
    def begin_execution(self, context: ExecutionContext) -> None:
        """Start tracing execution."""
        pass
    
    @abstractmethod
    def trace_rule_evaluation(self, rule: Rule, result: bool, 
                             context: ExecutionContext) -> None:
        """Trace rule evaluation."""
        pass
    
    @abstractmethod
    def trace_action_execution(self, rule: Rule, action: Any,
                              context: ExecutionContext) -> None:
        """Trace action execution."""
        pass
    
    @abstractmethod
    def end_execution(self, result: ExecutionResult, 
                     context: ExecutionContext) -> Dict[str, Any]:
        """End tracing and return trace data."""
        pass


class RuleLoader(ABC):
    """Loads rules from various sources."""
    
    @abstractmethod
    def load(self, source: Any) -> List[Rule]:
        """
        Load rules from source.
        
        Args:
            source: Rule source (file, string, dict, etc.)
            
        Returns:
            List of loaded rules
        """
        pass
    
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """Get list of supported formats."""
        pass


# Protocol for function registry (no ABC needed - duck typing)
class FunctionRegistry:
    """Registry for custom functions in expressions."""
    
    def register(self, name: str, func: callable) -> None:
        """Register a function."""
        raise NotImplementedError
    
    def get(self, name: str) -> Optional[callable]:
        """Get a function by name."""
        raise NotImplementedError
    
    def list_functions(self) -> List[str]:
        """List all registered functions."""
        raise NotImplementedError 