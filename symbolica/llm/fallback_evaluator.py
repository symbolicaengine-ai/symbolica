"""
Fallback Evaluator
==================

Implements the prompt() wrapper function that provides graceful degradation
from structured rule evaluation to LLM-based reasoning when data is missing
or malformed. This gives users the benefits of both deterministic rules and
intelligent AI fallback.

Usage Examples:
- prompt("credit_score > 700")  # Try structured evaluation first, LLM if missing data
- prompt("customer_tier == 'vip' and annual_income > 100000", "bool")  # With type hint
- prompt("Approve loan for {customer_name} with score {credit_score}", max_tokens=50)
"""

import logging
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass
from ..core.exceptions import EvaluationError, ValidationError
from .prompt_evaluator import PromptEvaluator
from .exceptions import LLMError


logger = logging.getLogger(__name__)


@dataclass
class FallbackResult:
    """Result of fallback evaluation showing which method was used."""
    value: Any
    method_used: str  # 'structured' or 'llm'
    structured_error: Optional[str] = None
    llm_reasoning: Optional[str] = None
    execution_time_ms: float = 0.0
    

class FallbackEvaluator:
    """
    Evaluator that wraps rule conditions with intelligent fallback.
    
    Tries structured evaluation first, then falls back to LLM when:
    - Required fields are missing
    - Data format is invalid
    - Expressions can't be parsed
    - Field values are None/null
    """
    
    def __init__(self, 
                 structured_evaluator,  # The core AST evaluator
                 prompt_evaluator: PromptEvaluator):
        """Initialize with both structured and LLM evaluators."""
        self.structured_evaluator = structured_evaluator
        self.prompt_evaluator = prompt_evaluator
        self._fallback_stats = {
            'total_calls': 0,
            'structured_success': 0,
            'llm_fallback': 0,
            'total_failures': 0
        }
    
    def prompt(self, 
               condition: str,
               return_type: str = "str",
               max_tokens: int = 100,
               context_facts: Optional[Dict[str, Any]] = None,
               rule_id: Optional[str] = None) -> FallbackResult:
        """
        Evaluate condition with graceful fallback to LLM.
        
        Args:
            condition: Rule condition or natural language description
            return_type: Expected return type (str, bool, int, float)
            max_tokens: Max tokens for LLM response
            context_facts: Available facts for evaluation
            rule_id: Optional rule ID for logging
            
        Returns:
            FallbackResult with value and method used
        """
        import time
        start_time = time.perf_counter()
        
        self._fallback_stats['total_calls'] += 1
        context_facts = context_facts or {}
        
        # Step 1: Try structured evaluation first
        try:
            structured_result = self._try_structured_evaluation(condition, context_facts)
            
            # Convert to expected type if needed
            if return_type != "str":
                structured_result = self._convert_type(structured_result, return_type)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            self._fallback_stats['structured_success'] += 1
            
            logger.debug(f"Structured evaluation succeeded for: {condition}")
            return FallbackResult(
                value=structured_result,
                method_used='structured',
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            # Log the structured evaluation error
            structured_error = str(e)
            logger.debug(f"Structured evaluation failed for '{condition}': {structured_error}")
            
            # Step 2: Fall back to LLM evaluation
            try:
                llm_result = self._try_llm_evaluation(
                    condition, return_type, max_tokens, context_facts, rule_id
                )
                
                execution_time = (time.perf_counter() - start_time) * 1000
                self._fallback_stats['llm_fallback'] += 1
                
                logger.info(f"LLM fallback succeeded for: {condition}")
                return FallbackResult(
                    value=llm_result['value'],
                    method_used='llm',
                    structured_error=structured_error,
                    llm_reasoning=llm_result.get('reasoning'),
                    execution_time_ms=execution_time
                )
                
            except Exception as llm_error:
                execution_time = (time.perf_counter() - start_time) * 1000
                self._fallback_stats['total_failures'] += 1
                
                logger.error(f"Both structured and LLM evaluation failed for '{condition}': "
                           f"Structured: {structured_error}, LLM: {str(llm_error)}")
                
                # Return default value based on type
                default_value = self._get_default_value(return_type)
                return FallbackResult(
                    value=default_value,
                    method_used='default',
                    structured_error=structured_error,
                    llm_reasoning=f"LLM error: {str(llm_error)}",
                    execution_time_ms=execution_time
                )
    
    def _try_structured_evaluation(self, condition: str, context_facts: Dict[str, Any]) -> Any:
        """Try to evaluate using structured rule engine."""
        # Create a mock execution context for evaluation
        from ..core.models import ExecutionContext, Facts
        
        # Create Facts object from context_facts
        original_facts = Facts(context_facts)
        
        # Create ExecutionContext with required arguments
        context = ExecutionContext(
            original_facts=original_facts,
            enriched_facts=context_facts.copy(),
            fired_rules=[]
        )
        
        # Try to evaluate the condition
        result = self.structured_evaluator.evaluate(condition, context)
        
        # Check if result depends on missing fields
        required_fields = self.structured_evaluator.extract_fields(condition)
        missing_fields = [field for field in required_fields 
                         if field not in context_facts or context_facts[field] is None]
        
        if missing_fields:
            raise EvaluationError(f"Missing required fields: {missing_fields}")
        
        return result
    
    def _try_llm_evaluation(self, 
                           condition: str, 
                           return_type: str, 
                           max_tokens: int,
                           context_facts: Dict[str, Any],
                           rule_id: Optional[str]) -> Dict[str, Any]:
        """Try to evaluate using LLM with enhanced context."""
        
        # Build enhanced prompt with context
        enhanced_prompt = self._build_enhanced_prompt(condition, context_facts, return_type)
        
        # Use the existing prompt evaluator
        llm_args = [enhanced_prompt]
        if return_type != "str":
            llm_args.append(return_type)
        if max_tokens != 100:
            llm_args.append(max_tokens)
        
        result = self.prompt_evaluator.evaluate_prompt(
            llm_args, 
            context_facts, 
            rule_id=rule_id
        )
        
        return {
            'value': result,
            'reasoning': f"LLM evaluated: {condition} with available data"
        }
    
    def _build_enhanced_prompt(self, 
                              condition: str, 
                              context_facts: Dict[str, Any],
                              return_type: str) -> str:
        """Build an enhanced prompt with available context and clear instructions."""
        
        available_data = {k: v for k, v in context_facts.items() if v is not None}
        missing_data = {k: v for k, v in context_facts.items() if v is None}
        
        prompt_parts = [
            f"Evaluate this business rule: {condition}",
            "",
            "Available data:"
        ]
        
        if available_data:
            for key, value in available_data.items():
                prompt_parts.append(f"- {key}: {value}")
        else:
            prompt_parts.append("- No complete data available")
        
        if missing_data:
            prompt_parts.append("")
            prompt_parts.append("Missing/incomplete data:")
            for key, value in missing_data.items():
                prompt_parts.append(f"- {key}: {value if value is not None else 'missing'}")
        
        prompt_parts.extend([
            "",
            f"Based on the available information, provide a {return_type} response.",
            "Use reasonable business logic and common sense for missing data.",
            f"Respond with only the {return_type} value, no explanation."
        ])
        
        return "\n".join(prompt_parts)
    
    def _convert_type(self, value: Any, return_type: str) -> Any:
        """Convert value to expected type."""
        if return_type == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        elif return_type == "int":
            return int(float(value))  # Handle string numbers
        elif return_type == "float":
            return float(value)
        else:  # str
            return str(value)
    
    def _get_default_value(self, return_type: str) -> Any:
        """Get safe default value for type."""
        defaults = {
            'bool': False,
            'int': 0,
            'float': 0.0,
            'str': ''
        }
        return defaults.get(return_type, None)
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """Get statistics about fallback usage."""
        total = self._fallback_stats['total_calls']
        if total == 0:
            return self._fallback_stats
        
        return {
            **self._fallback_stats,
            'structured_success_rate': self._fallback_stats['structured_success'] / total,
            'llm_fallback_rate': self._fallback_stats['llm_fallback'] / total,
            'failure_rate': self._fallback_stats['total_failures'] / total
        }
    
    def reset_stats(self) -> None:
        """Reset fallback statistics."""
        self._fallback_stats = {
            'total_calls': 0,
            'structured_success': 0,
            'llm_fallback': 0,
            'total_failures': 0
        } 