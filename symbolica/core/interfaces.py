"""
Symbolica Core Interfaces
=========================

Minimal interfaces for core functionality only.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Rule, Facts, ExecutionResult, ExecutionContext


class ConditionEvaluator(ABC):
    """Evaluates rule conditions against facts using AST parsing."""
    
    @abstractmethod
    def evaluate(self, condition_expr: str, context: 'ExecutionContext') -> bool:
        """
        Evaluate condition expression against execution context.
        
        Args:
            condition_expr: The condition expression string to evaluate
            context: Current execution context with facts
            
        Returns:
            True if condition is satisfied
        """
        pass
    
    @abstractmethod  
    def extract_fields(self, condition_expr: str) -> Set[str]:
        """
        Extract field names referenced by the condition (needed for DAG dependencies).
        
        Args:
            condition_expr: The condition expression to analyze
            
        Returns:
            Set of field names referenced
        """
        pass


class ExecutionStrategy(ABC):
    """Strategy for ordering rule execution based on dependencies."""
    
    @abstractmethod
    def get_execution_order(self, rules: List['Rule']) -> List['Rule']:
        """
        Get the order in which rules should be executed.
        
        Args:
            rules: List of rules to order
            
        Returns:
            Rules in execution order
        """
        pass 