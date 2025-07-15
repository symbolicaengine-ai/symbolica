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
import re


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
    
    def _analyze_evaluation_error(self, error_msg: str, context_facts: Dict[str, Any]) -> tuple[str, str]:
        """
        Analyze the evaluation error to identify the problematic field and issue.
        
        Returns:
            tuple: (field_name, issue_description)
        """
        error_msg_lower = error_msg.lower()
        
        # Check for missing fields
        missing_field_patterns = [
            r"'([^']+)' is not defined",
            r"name '([^']+)' is not defined",
            r"missing field[s]?\s*:?\s*([a-zA-Z_][a-zA-Z0-9_]*)",
            r"field '([^']+)' not found",
            r"unknown field[s]?\s*:?\s*([a-zA-Z_][a-zA-Z0-9_]*)"
        ]
        
        for pattern in missing_field_patterns:
            match = re.search(pattern, error_msg_lower)
            if match:
                field_name = match.group(1)
                return field_name, "field is missing or undefined"
        
        # Check for type conversion errors
        type_error_patterns = [
            r"unsupported operand type\(s\) for .+: '(.+)' and",
            r"can't convert (.+) to (\w+)",
            r"invalid literal for (\w+)\(\) with base \d+: '([^']+)'",
            r"could not convert string to (\w+): '([^']+)'"
        ]
        
        for pattern in type_error_patterns:
            match = re.search(pattern, error_msg_lower)
            if match:
                # Try to find the field name in context that has this problematic value
                if len(match.groups()) >= 2:
                    problematic_value = match.group(2) if len(match.groups()) >= 2 else match.group(1)
                    for field_name, field_value in context_facts.items():
                        if str(field_value) == problematic_value:
                            return field_name, f"type conversion error - value '{problematic_value}' cannot be converted to number"
                return "unknown_field", f"type conversion error - {match.group(0)}"
        
        # Check for None/null value errors
        if 'nonetype' in error_msg_lower or 'none' in error_msg_lower:
            # Try to find None values in context
            none_fields = [field for field, value in context_facts.items() if value is None]
            if none_fields:
                return none_fields[0], "field value is None/null"
            return "unknown_field", "encountered None/null value"
        
        # Check for comparison errors with strings
        if '>=' in error_msg_lower or '<=' in error_msg_lower or '>' in error_msg_lower or '<' in error_msg_lower:
            for field_name, field_value in context_facts.items():
                if isinstance(field_value, str) and not field_value.replace('.', '').replace('-', '').isdigit():
                    return field_name, f"cannot compare text value '{field_value}' numerically"
        
        # General fallback - try to extract any field name from the error
        field_name_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        field_matches = re.findall(field_name_pattern, error_msg)
        for potential_field in field_matches:
            if potential_field in context_facts:
                return potential_field, "evaluation error"
        
        return "unknown_field", "evaluation error"
    
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
            
            # Analyze the error to provide better console logging
            problematic_field, issue_description = self._analyze_evaluation_error(structured_error, context_facts)
            
            # Console logging for LLM fallback activation
            rule_context = f" (Rule: {rule_id})" if rule_id else ""
            print(f"🔄 Falling back to LLM for '{problematic_field}' because {issue_description}{rule_context}")
            
            # Step 2: Fall back to LLM evaluation
            try:
                llm_result = self._try_llm_evaluation(
                    condition, return_type, max_tokens, context_facts, rule_id
                )
                
                execution_time = (time.perf_counter() - start_time) * 1000
                self._fallback_stats['llm_fallback'] += 1
                
                logger.info(f"LLM fallback succeeded for: {condition}")
                print(f"✅ LLM fallback completed successfully for '{problematic_field}'")
                
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
                
                print(f"❌ LLM fallback failed for '{problematic_field}': {str(llm_error)}")
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
        
        # Try to evaluate the condition - let it handle missing fields naturally
        result = self.structured_evaluator.evaluate(condition, context)
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