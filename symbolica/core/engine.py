"""
Symbolica Rule Engine
=====================

Simple, deterministic rule engine for AI agent decision-making.
Refactored to use focused components following Single Responsibility Principle.
"""

import time
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable

from .models import Rule, Facts, ExecutionContext, ExecutionResult, Goal, facts
from .exceptions import (
    ValidationError, ExecutionError, EvaluationError, 
    DAGError, ConfigurationError, ErrorCollector, FunctionError
)
from .services.loader import RuleLoader
from .services.function_registry import FunctionRegistry
from .validation.validation_service import ValidationService
from .services.temporal_service import TemporalService
from .._internal.evaluation.evaluator import ASTEvaluator
from .._internal.strategies.dag import DAGStrategy
from .._internal.strategies.backward_chainer import BackwardChainer


class Engine:
    """Simple rule engine for AI agents.
    
    Orchestrates rule execution using focused, single-responsibility components.
    No longer a God Class - delegates specific responsibilities to specialized services.
    """
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.logger = logging.getLogger(f'symbolica.{cls.__name__}')
    
    def __init__(self, 
                 rules: Optional[List[Rule]] = None,
                 temporal_config: Optional[Dict[str, Any]] = None,
                 execution_config: Optional[Dict[str, Any]] = None,
                 llm_client: Optional[Any] = None,
                 llm_config: Optional[Dict[str, Any]] = None):
        """Initialize engine with rules and optional configuration.
        
        Args:
            rules: Optional list of rules to initialize with
            temporal_config: Optional temporal service configuration
            execution_config: Optional execution configuration (max_iterations, etc.)
            llm_client: Optional LLM client for PROMPT() function support
            llm_config: Optional LLM configuration dictionary
        """
        # Initialize logger
        self.logger = logging.getLogger('symbolica.Engine')
        
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
        
        # Initialize LLM integration if client provided
        self._prompt_evaluator = None
        if llm_client:
            try:
                from ..llm import LLMClientAdapter, LLMConfig
                from ..llm.prompt_evaluator import PromptEvaluator
                
                # Create LLM configuration
                llm_config = llm_config or {}
                config = LLMConfig.from_dict(llm_config)
                
                # Create client adapter
                adapter = LLMClientAdapter(llm_client, config)
                
                # Create prompt evaluator
                self._prompt_evaluator = PromptEvaluator(adapter)
                
                self.logger.info("LLM integration enabled with PROMPT() function support")
                
            except ImportError as e:
                self.logger.warning(f"LLM integration failed - missing dependencies: {e}")
                self._prompt_evaluator = None
            except Exception as e:
                self.logger.error(f"LLM integration failed: {e}")
                self._prompt_evaluator = None
        
        # Initialize execution components (pass LLM evaluator to ASTEvaluator)
        self._evaluator = ASTEvaluator(prompt_evaluator=self._prompt_evaluator)
        self._executor = self._evaluator
        self._dag_strategy = DAGStrategy(self._evaluator)
        self._backward_chainer = BackwardChainer(self._rules, self._evaluator)
        
        # Register temporal functions and built-in functions
        self._setup_functions()
        
        # Validate rules if provided
        if self._rules:
            self._validation_service.validate_rules(self._rules)
    
    def _setup_functions(self) -> None:
        """Set up function registrations."""
        # Register temporal functions (these are system functions, bypass normal validation)
        self._temporal_service.register_temporal_functions(self._function_registry)
        
        # Connect function registry to evaluator (system functions need special handling)
        for name, func in self._function_registry._functions.items():
            # System functions bypass normal validation in evaluator too
            self._evaluator._core.register_function(name, func)
            self._evaluator._trace_evaluator.register_function(name, func)
            self._evaluator._execution_path_evaluator.register_function(name, func)
            # Update field extractor
            self._evaluator._update_function_registry()
    
    def _is_expression(self, value: Any) -> bool:
        """Detect if a value should be treated as an expression to evaluate.
        
        Args:
            value: Value to check
            
        Returns:
            True if value appears to be an expression, False otherwise
        """
        if not isinstance(value, str):
            return False
        
        # Skip empty strings
        if not value.strip():
            return False
        
        # Check for arithmetic operators
        arithmetic_ops = ['+', '-', '*', '/', '//', '%', '**']
        has_arithmetic = any(op in value for op in arithmetic_ops)
        
        # Check for parentheses (likely mathematical expression)
        has_parentheses = '(' in value and ')' in value
        
        # Check for function calls (word followed by parentheses)
        has_function_call = re.search(r'\w+\s*\(', value)
        
        # Check for comparison operators 
        comparison_ops = ['==', '!=', '<', '>', '<=', '>=']
        has_comparisons = any(op in value for op in comparison_ops)
        
        # Check for template variables ({{ variable }})
        has_templates = '{{' in value and '}}' in value
        
        # Check for boolean/logical operators
        logical_ops = [' and ', ' or ', ' not ', ' in ', ' is ']
        has_logical = any(op in value for op in logical_ops)
        
        # Only treat as expression if it has clear expression indicators
        # Do NOT treat single words as expressions - they're usually literal strings
        is_likely_expression = (
            has_arithmetic or 
            has_parentheses or 
            has_function_call or
            has_comparisons or
            has_templates or
            has_logical
        )
        
        # Additional checks to avoid false positives
        # Skip if it's clearly a sentence (multiple words with spaces and no operators)
        if ' ' in value and not any(op in value for op in arithmetic_ops + comparison_ops + logical_ops) and not has_parentheses:
            return False
        
        # Skip if it looks like a URL, file path, or other string literal
        if any(pattern in value.lower() for pattern in ['http://', 'https://', '\\', '/', '.com', '.org']):
            return False
        
        return is_likely_expression
    
    def _evaluate_action_value(self, value: Any, context: ExecutionContext) -> Any:
        """Evaluate an action value, computing expressions as numbers.
        
        Args:
            value: Raw action value from rule
            context: Current execution context
            
        Returns:
            Evaluated value (computed if expression, original if literal)
        """
        # Only attempt evaluation for potential expressions
        if not self._is_expression(value):
            return value
        
        try:
            # Use the same evaluator as conditions
            result, _ = self._evaluator._core.evaluate(str(value), context)
            return result
        except Exception:
            # If evaluation fails, return original value
            # This ensures backward compatibility
            return value
    
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
        # Register with function registry (this validates against reserved keywords)
        self._function_registry.register_function(name, func, allow_unsafe)
        # Also register with evaluator components directly (validation already done)
        self._evaluator._core.register_function(name, func)
        self._evaluator._trace_evaluator.register_function(name, func)
        self._evaluator._execution_path_evaluator.register_function(name, func)
        # Update field extractor
        self._evaluator._update_function_registry()
    
    def unregister_function(self, name: str) -> None:
        """Remove a registered custom function."""
        self._function_registry.unregister_function(name)
        # Also unregister from evaluator components
        self._evaluator._core.unregister_function(name)
        self._evaluator._trace_evaluator.unregister_function(name)
        self._evaluator._execution_path_evaluator.unregister_function(name)
        # Update field extractor
        self._evaluator._update_function_registry()
    
    def list_functions(self) -> Dict[str, str]:
        """List all available functions (built-in + custom + temporal + LLM)."""
        # Combine built-in functions from evaluator with custom functions
        builtin_functions = {
            'len': 'Get length of sequence',
            'sum': 'Sum elements of sequence', 
            'abs': 'Absolute value',
            'startswith': 'Check if string starts with substring',
            'endswith': 'Check if string ends with substring',
            'contains': 'Check if sequence contains element'
        }
        
        # Add LLM functions if available
        if self._prompt_evaluator:
            builtin_functions['PROMPT'] = 'Execute LLM prompt with variable substitution and type conversion'
        
        custom_functions = self._function_registry.list_functions_with_descriptions()
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
        
        # Build result with context for hierarchical tracing
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ms=execution_time_ms,
            reasoning=context.reasoning,
            intermediate_facts=context.intermediate_facts,
            _context=context  # Store context for rich tracing access
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
        except Exception as e:
            # Log the DAG failure and use priority fallback
            self.logger.warning(
                f"DAG strategy failed, falling back to priority ordering: {str(e)}",
                extra={'rule_count': len(rules), 'rule_ids': [r.id for r in rules]}
            )
            return sorted(rules, key=lambda r: r.priority, reverse=True)
    
    def _can_rule_fire(self, rule: Rule, context: ExecutionContext) -> bool:
        """Check if a rule's condition is satisfied and it hasn't fired yet."""
        if rule.id in context.fired_rules:
            return False
            
        try:
            trace = self._evaluator.evaluate_with_trace(rule.condition, context)
            return trace.result
        except (EvaluationError, FunctionError) as e:
            # Log evaluation failures but continue execution
            self.logger.warning(
                f"Rule condition evaluation failed for rule '{rule.id}': {str(e)}",
                extra={'rule_id': rule.id, 'condition': rule.condition}
            )
            return False
        except Exception as e:
            # Log unexpected errors but continue execution
            self.logger.error(
                f"Unexpected error evaluating rule '{rule.id}': {str(e)}",
                extra={'rule_id': rule.id, 'condition': rule.condition}
            )
            return False
    
    def _execute_rule(self, rule: Rule, context: ExecutionContext, triggered_by: Optional[str] = None) -> bool:
        """Execute a single rule with proper error handling.
        
        Returns:
            True if the rule fired, False otherwise
        """
        try:
            # Evaluate with execution path for detailed analysis
            if hasattr(self._evaluator, 'evaluate_with_execution_path'):
                execution_path = self._evaluator.evaluate_with_execution_path(rule.condition, context)
                # Store the execution path for LLM processing
                context.store_rule_trace(rule.id, execution_path)
                
                # Use execution path results
                trace_result = execution_path.result
                detailed_reason = execution_path.explain()
            else:
                # Fallback to simple trace
                trace = self._evaluator.evaluate_with_trace(rule.condition, context)
                trace_result = trace.result
                detailed_reason = trace.explain()
            
            if trace_result:
                # Apply facts first (intermediate state available to other rules)
                evaluated_facts = {}
                if rule.facts:
                    for key, value in rule.facts.items():
                        # Evaluate expressions, keep literals as-is
                        evaluated_value = self._evaluate_action_value(value, context)
                        context.set_intermediate_fact(key, evaluated_value)
                        evaluated_facts[key] = evaluated_value
                
                # Apply actions (final outputs)
                evaluated_actions = {}
                for key, value in rule.actions.items():
                    # Evaluate expressions, keep literals as-is
                    evaluated_value = self._evaluate_action_value(value, context)
                    context.set_fact(key, evaluated_value)
                    evaluated_actions[key] = evaluated_value
                
                # Record detailed reasoning using trace
                fact_items = [f"{k}={v}" for k, v in evaluated_facts.items()] if evaluated_facts else []
                action_items = [f"{k}={v}" for k, v in evaluated_actions.items()]
                
                if fact_items and action_items:
                    outputs_str = f"facts: {', '.join(fact_items)}, actions: {', '.join(action_items)}"
                elif fact_items:
                    outputs_str = f"facts: {', '.join(fact_items)}"
                else:
                    outputs_str = f"actions: {', '.join(action_items)}"
                
                reason = f"{detailed_reason}, set {outputs_str}"
                context.rule_fired(rule.id, reason, triggered_by)
                
                return True
                
        except (EvaluationError, FunctionError) as e:
            # Rule execution failed - log and record in context
            self.logger.warning(
                f"Rule execution failed for rule '{rule.id}': {str(e)}",
                extra={'rule_id': rule.id, 'condition': rule.condition, 'triggered_by': triggered_by}
            )
            context.rule_fired(rule.id, f"Rule execution failed: {str(e)}", triggered_by)
        except (AttributeError, TypeError, ValueError, SyntaxError) as e:
            # Python evaluation errors - log and record
            self.logger.warning(
                f"Python evaluation error in rule '{rule.id}': {str(e)}",
                extra={'rule_id': rule.id, 'condition': rule.condition}
            )
            context.rule_fired(rule.id, f"Rule execution failed: {str(e)}", triggered_by)
        except Exception as e:
            # Unexpected error - log as error and continue
            self.logger.error(
                f"Unexpected error in rule '{rule.id}': {str(e)}",
                extra={'rule_id': rule.id, 'condition': rule.condition, 'triggered_by': triggered_by}
            )
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
        
        avg_priority = sum(rule.priority for rule in self._rules) / len(self._rules) if self._rules else 0
        
        analysis = {
            'rule_count': len(self._rules),  # Add rule_count at top level for backward compatibility
            'rule_ids': [rule.id for rule in self._rules],  # Add rule_ids at top level for backward compatibility
            'avg_priority': avg_priority,  # Add avg_priority at top level for backward compatibility
            'rule_analysis': {
                'rule_count': len(self._rules),
                'rule_ids': [rule.id for rule in self._rules],
                'avg_priority': avg_priority,
                **dependency_analysis
            },
            'temporal_analysis': temporal_stats,
            'function_analysis': function_stats
        }
        return analysis
    
    @property
    def rules(self) -> List[Rule]:
        """Get all rules (read-only copy)."""
        return self._rules.copy()
    
    @property
    def rule_count(self) -> int:
        """Get rule count."""
        return len(self._rules) 