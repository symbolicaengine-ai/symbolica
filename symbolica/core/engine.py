"""
Symbolica Rule Engine
=====================

Simple, deterministic rule engine for AI agent decision-making.
Refactored to use focused components following Single Responsibility Principle.
"""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable

from .models import Rule, Facts, ExecutionContext, ExecutionResult, Goal, facts
from .exceptions import ValidationError
from .loader import RuleLoader
from .function_registry import FunctionRegistry
from .validation_service import ValidationService
from .temporal_service import TemporalService
from .._internal.evaluator import ASTEvaluator
from .._internal.dag import DAGStrategy
from .._internal.backward_chainer import BackwardChainer


class Engine:
    """Simple rule engine for AI agents.
    
    Orchestrates rule execution using focused, single-responsibility components.
    No longer a God Class - delegates specific responsibilities to specialized services.
    """
    
    def __init__(self, 
                 rules: Optional[List[Rule]] = None,
                 temporal_config: Optional[Dict[str, Any]] = None,
                 execution_config: Optional[Dict[str, Any]] = None):
        """Initialize engine with rules and optional configuration.
        
        Args:
            rules: Optional list of rules to initialize with
            temporal_config: Optional temporal service configuration
            execution_config: Optional execution configuration (max_iterations, etc.)
        """
        # Initialize core components
        self._rules = rules or []
        self._function_registry = FunctionRegistry()
        self._validation_service = ValidationService()
        self._rule_loader = RuleLoader()
        
        # Initialize temporal service with configuration
        temporal_config = temporal_config or {}
        self._temporal_service = TemporalService(
            max_age_seconds=temporal_config.get('max_age_seconds', 3600),
            max_points_per_key=temporal_config.get('max_points_per_key', 1000),
            cleanup_interval=temporal_config.get('cleanup_interval', 300)
        )
        
        # Initialize execution configuration
        execution_config = execution_config or {}
        self._max_iterations = execution_config.get('max_iterations', 10)
        
        # Initialize execution components
        self._evaluator = ASTEvaluator()
        self._dag_strategy = DAGStrategy(self._evaluator)
        self._backward_chainer = BackwardChainer(self._rules, self._evaluator)
        
        # Register temporal functions and built-in functions
        self._setup_functions()
        
        # Validate rules if provided
        if self._rules:
            self._validation_service.validate_rules(self._rules)
    
    def _setup_functions(self) -> None:
        """Set up function registrations."""
        # Register temporal functions
        self._temporal_service.register_temporal_functions(self._function_registry)
        
        # Connect function registry to evaluator
        for name, func in self._function_registry._functions.items():
            self._evaluator.register_function(name, func)
    
    # Rule Loading Methods (delegated to RuleLoader)
    @classmethod
    def from_yaml(cls, yaml_content: str, **kwargs) -> 'Engine':
        """Create engine from YAML string."""
        loader = RuleLoader()
        rules = loader.from_yaml(yaml_content)
        return cls(rules, **kwargs)
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path], **kwargs) -> 'Engine':
        """Create engine from YAML file."""
        loader = RuleLoader()
        rules = loader.from_file(file_path)
        return cls(rules, **kwargs)
    
    @classmethod
    def from_directory(cls, directory_path: Union[str, Path], **kwargs) -> 'Engine':
        """Create engine from directory containing YAML files."""
        loader = RuleLoader()
        rules = loader.from_directory(directory_path)
        return cls(rules, **kwargs)
    
    # Function Management (delegated to FunctionRegistry)
    def register_function(self, name: str, func: Callable, allow_unsafe: bool = False) -> None:
        """Register a custom function for use in rule conditions.
        
        Args:
            name: Function name to use in conditions
            func: Callable function (lambda recommended for safety)
            allow_unsafe: If True, allows full functions (use with caution)
        """
        self._function_registry.register_function(name, func, allow_unsafe)
        # Also register with evaluator
        self._evaluator.register_function(name, func)
    
    def unregister_function(self, name: str) -> None:
        """Remove a registered custom function."""
        self._function_registry.unregister_function(name)
        self._evaluator.unregister_function(name)
    
    def list_functions(self) -> Dict[str, str]:
        """List all available functions (built-in + custom + temporal)."""
        # Combine built-in functions from evaluator with custom functions
        builtin_functions = {
            'len': 'Get length of sequence',
            'sum': 'Sum elements of sequence', 
            'abs': 'Absolute value',
            'startswith': 'Check if string starts with substring',
            'endswith': 'Check if string ends with substring',
            'contains': 'Check if sequence contains element'
        }
        custom_functions = self._function_registry.list_functions()
        return {**builtin_functions, **custom_functions}
    
    # Temporal Operations (delegated to TemporalService)
    def store_datapoint(self, key: str, value: float, timestamp: Optional[float] = None) -> None:
        """Store a time-series data point for use in temporal functions."""
        self._temporal_service.store_datapoint(key, value, timestamp)
    
    def set_ttl_fact(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a fact with time-to-live (TTL)."""
        self._temporal_service.set_ttl_fact(key, value, ttl_seconds)
    
    def get_temporal_stats(self) -> Dict[str, Any]:
        """Get temporal store statistics."""
        return self._temporal_service.get_stats()
    
    def cleanup_temporal_data(self) -> Dict[str, int]:
        """Force cleanup of old temporal data."""
        return self._temporal_service.cleanup_old_data()
    
    # Core Execution Logic (simplified and focused)  
    def reason(self, input_facts: Union[Facts, Dict[str, Any]]) -> ExecutionResult:
        """Execute rules against facts and return result with explanation."""
        start_time = time.perf_counter()
        
        # Convert dictionary to Facts if needed
        if isinstance(input_facts, dict):
            input_facts = Facts(input_facts)
        
        # Create execution context
        context = ExecutionContext(
            original_facts=input_facts,
            enriched_facts={},
            fired_rules=[]
        )
        
        # Execute rules iteratively until convergence
        self._execute_rules_iteratively(context)
        
        # Build result
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ms=execution_time_ms,
            reasoning=context.reasoning
        )
    
    def _execute_rules_iteratively(self, context: ExecutionContext) -> None:
        """Execute rules iteratively until no new rules fire (convergence)."""
        
        for iteration in range(self._max_iterations):
            rules_fired_this_iteration = 0
            
            # Get rules that haven't fired yet
            remaining_rules = [rule for rule in self._rules if rule.id not in context.fired_rules]
            if not remaining_rules:
                break
            
            # Get execution order (dependency-aware with priority fallback)
            execution_order = self._get_execution_order(remaining_rules)
            
            # Execute rules that can fire
            for rule in execution_order:
                if self._can_rule_fire(rule, context):
                    triggered_by = self._find_triggering_rule(rule, context.fired_rules)
                    if self._execute_rule(rule, context, triggered_by):
                        rules_fired_this_iteration += 1
            
            # If no rules fired this iteration, we've reached convergence
            if rules_fired_this_iteration == 0:
                break
    
    def _get_execution_order(self, rules: List[Rule]) -> List[Rule]:
        """Get rule execution order with DAG strategy and priority fallback."""
        try:
            return self._dag_strategy.get_execution_order(rules)
        except Exception:
            # Fallback to priority-based sorting if DAG fails
            return sorted(rules, key=lambda r: r.priority, reverse=True)
    
    def _can_rule_fire(self, rule: Rule, context: ExecutionContext) -> bool:
        """Check if a rule's condition is satisfied and it hasn't fired yet."""
        if rule.id in context.fired_rules:
            return False
            
        try:
            trace = self._evaluator.evaluate_with_trace(rule.condition, context)
            return trace.result
        except Exception:
            return False
    
    def _execute_rule(self, rule: Rule, context: ExecutionContext, triggered_by: Optional[str] = None) -> bool:
        """Execute a single rule with proper error handling.
        
        Returns:
            True if the rule fired, False otherwise
        """
        try:
            # Evaluate with trace to get detailed explanation
            trace = self._evaluator.evaluate_with_trace(rule.condition, context)
            
            if trace.result:
                # Apply actions
                for key, value in rule.actions.items():
                    context.set_fact(key, value)
                
                # Record detailed reasoning using trace
                detailed_reason = trace.explain()
                actions_str = ", ".join([f"{k}={v}" for k, v in rule.actions.items()])
                reason = f"{detailed_reason}, set {actions_str}"
                context.rule_fired(rule.id, reason, triggered_by)
                
                return True
                
        except (AttributeError, TypeError, ValueError, SyntaxError) as e:
            # Rule execution failed - continue with other rules but record failure
            # In a production system, this should use proper logging
            context.rule_fired(rule.id, f"Rule execution failed: {str(e)}", triggered_by)
        except Exception as e:
            # Unexpected error - continue execution but log the issue
            context.rule_fired(rule.id, f"Unexpected error in rule: {str(e)}", triggered_by)
        
        return False
    
    def _find_triggering_rule(self, rule: Rule, fired_rules: List[str]) -> Optional[str]:
        """Find which rule triggered this rule, if any."""
        for fired_rule_id in fired_rules:
            fired_rule = next((r for r in self._rules if r.id == fired_rule_id), None)
            if fired_rule and rule.id in fired_rule.triggers:
                return fired_rule_id
        return None
    
    # Backward Chaining (delegated to BackwardChainer)
    def find_rules_for_goal(self, goal: Goal) -> List[Rule]:
        """Find rules that can produce the goal (reverse DAG search)."""
        return self._backward_chainer.find_supporting_rules(goal)
    
    def can_achieve_goal(self, goal: Goal, current_facts: Union[Facts, Dict[str, Any]]) -> bool:
        """Test if goal can be achieved with current facts."""
        if isinstance(current_facts, dict):
            current_facts = Facts(current_facts)
        
        return self._backward_chainer.can_achieve_goal(goal, current_facts)
    
    # Rule Management
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine.
        
        Args:
            rule: Rule to add
            
        Raises:
            ValidationError: If rule is invalid or conflicts with existing rules
        """
        # Validate the new rule
        self._validation_service._validate_single_rule(rule)
        
        # Check for ID conflicts
        if any(r.id == rule.id for r in self._rules):
            raise ValidationError(f"Rule with ID '{rule.id}' already exists")
        
        # Add rule
        self._rules.append(rule)
        
        # Validate the complete rule set
        self._validation_service.validate_rules(self._rules)
        
        # Update backward chainer
        self._backward_chainer = BackwardChainer(self._rules, self._evaluator)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID.
        
        Args:
            rule_id: ID of rule to remove
            
        Returns:
            True if rule was removed, False if not found
        """
        original_count = len(self._rules)
        self._rules = [r for r in self._rules if r.id != rule_id]
        
        if len(self._rules) < original_count:
            # Re-validate remaining rules
            self._validation_service.validate_rules(self._rules)
            # Update backward chainer
            self._backward_chainer = BackwardChainer(self._rules, self._evaluator)
            return True
        
        return False
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID."""
        return next((rule for rule in self._rules if rule.id == rule_id), None)
    
    def update_rule(self, rule_id: str, updated_rule: Rule) -> bool:
        """Update an existing rule.
        
        Args:
            rule_id: ID of rule to update
            updated_rule: New rule definition
            
        Returns:
            True if rule was updated, False if not found
            
        Raises:
            ValidationError: If updated rule is invalid
        """
        # Find rule index
        rule_index = None
        for i, rule in enumerate(self._rules):
            if rule.id == rule_id:
                rule_index = i
                break
        
        if rule_index is None:
            return False
        
        # Validate updated rule
        self._validation_service._validate_single_rule(updated_rule)
        
        # Check if ID changed and conflicts
        if updated_rule.id != rule_id:
            if any(r.id == updated_rule.id for r in self._rules):
                raise ValidationError(f"Rule with ID '{updated_rule.id}' already exists")
        
        # Update rule
        self._rules[rule_index] = updated_rule
        
        # Validate the complete rule set
        self._validation_service.validate_rules(self._rules)
        
        # Update backward chainer
        self._backward_chainer = BackwardChainer(self._rules, self._evaluator)
        
        return True
    
    # Analytics and Introspection
    def get_analysis(self) -> Dict[str, Any]:
        """Get comprehensive analysis of the rule engine."""
        dependency_analysis = self._validation_service.get_dependency_analysis(self._rules)
        temporal_stats = self._temporal_service.get_stats()
        function_stats = {
            'custom_functions': self._function_registry.function_count(),
            'total_functions': len(self.list_functions())
        }
        
        return {
            'rule_analysis': {
                'rule_count': len(self._rules),
                'rule_ids': [rule.id for rule in self._rules],
                'avg_priority': sum(rule.priority for rule in self._rules) / len(self._rules) if self._rules else 0,
                **dependency_analysis
            },
            'temporal_analysis': temporal_stats,
            'function_analysis': function_stats
        }
    
    @property
    def rules(self) -> List[Rule]:
        """Get all rules (read-only copy)."""
        return self._rules.copy()
    
    @property
    def rule_count(self) -> int:
        """Get rule count."""
        return len(self._rules) 