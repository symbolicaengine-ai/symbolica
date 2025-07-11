"""
Prompt Evaluator
================

Implements the PROMPT() function for rule evaluation.
Includes basic safety features and type conversion.
"""

import re
import logging
from typing import Any, List, Union
from .client_adapter import LLMClientAdapter
from .exceptions import LLMError, LLMValidationError
from ..core.exceptions import EvaluationError


logger = logging.getLogger(__name__)


class PromptSanitizer:
    """Simple prompt sanitization to prevent basic injection attacks."""
    
    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """Basic prompt sanitization."""
        # Truncate if too long
        if len(prompt) > 2000:
            prompt = prompt[:2000] + "..."
        
        # Escape quotes to prevent prompt breakage
        prompt = prompt.replace('"', '\\"').replace("'", "\\'")
        
        # Remove potential instruction injection patterns (basic)
        dangerous_patterns = [
            "ignore previous instructions",
            "disregard the above",
            "new instructions:",
            "system:",
            "assistant:"
        ]
        
        for pattern in dangerous_patterns:
            prompt = prompt.replace(pattern, "[FILTERED]")
            prompt = prompt.replace(pattern.upper(), "[FILTERED]")
            prompt = prompt.replace(pattern.title(), "[FILTERED]")
        
        return prompt
    
    @staticmethod
    def sanitize_variable(value: Any) -> str:
        """Sanitize a variable value before including in prompt."""
        # Convert to string and truncate
        str_value = str(value)
        if len(str_value) > 500:
            str_value = str_value[:500] + "..."
        
        # Basic sanitization
        return PromptSanitizer.sanitize_prompt(str_value)


class OutputValidator:
    """Validates and converts LLM outputs to expected types."""
    
    @staticmethod
    def validate_and_convert(response: str, return_type: str) -> Any:
        """Validate LLM response and convert to expected type."""
        if not response:
            return OutputValidator._get_default_value(return_type)
        
        # Truncate if too long
        if len(response) > 200:
            response = response[:200]
        
        # Remove leading/trailing whitespace
        response = response.strip()
        
        try:
            if return_type == "str":
                return response
            elif return_type == "int":
                return OutputValidator._extract_int(response)
            elif return_type == "float":
                return OutputValidator._extract_float(response)
            elif return_type == "bool":
                return OutputValidator._extract_bool(response)
            else:
                raise LLMValidationError(f"Unsupported return type: {return_type}")
        except Exception as e:
            logger.warning(f"Failed to convert LLM response '{response}' to {return_type}: {e}")
            return OutputValidator._get_default_value(return_type)
    
    @staticmethod
    def _extract_int(response: str) -> int:
        """Extract integer from response with fallback."""
        # Look for first number in response
        numbers = re.findall(r'-?\d+', response)
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                pass
        
        # Try word-to-number conversion for common cases
        word_to_num = {
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }
        
        response_lower = response.lower()
        for word, num in word_to_num.items():
            if word in response_lower:
                return num
        
        # Fallback
        return 0
    
    @staticmethod
    def _extract_float(response: str) -> float:
        """Extract float from response with fallback."""
        # Look for first number (including decimals)
        numbers = re.findall(r'-?\d+\.?\d*', response)
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        
        # Fallback to int extraction
        return float(OutputValidator._extract_int(response))
    
    @staticmethod
    def _extract_bool(response: str) -> bool:
        """Extract boolean from response with fallback."""
        response_lower = response.lower().strip()
        
        # Direct positive matches
        positive_words = ["true", "yes", "y", "1", "positive", "correct", "good", "approve", "accept"]
        if any(word in response_lower for word in positive_words):
            return True
        
        # Direct negative matches  
        negative_words = ["false", "no", "n", "0", "negative", "incorrect", "bad", "reject", "deny"]
        if any(word in response_lower for word in negative_words):
            return False
        
        # Default to False for ambiguous responses
        return False
    
    @staticmethod
    def _get_default_value(return_type: str) -> Any:
        """Get default value for a type when conversion fails."""
        defaults = {
            "str": "",
            "int": 0,
            "float": 0.0,
            "bool": False
        }
        return defaults.get(return_type, "")


class PromptEvaluator:
    """Evaluates PROMPT() function calls within rule conditions."""
    
    def __init__(self, llm_adapter: LLMClientAdapter):
        self.llm_adapter = llm_adapter
        self.sanitizer = PromptSanitizer()
        self.validator = OutputValidator()
    
    def evaluate_prompt(self, args: List[Any], context_facts: dict) -> Any:
        """
        Evaluate PROMPT() function call.
        
        Args:
            args: Function arguments [prompt_template, return_type?, max_tokens?]
            context_facts: Available facts for variable substitution
            
        Returns:
            Converted LLM response in requested type
        """
        # Validate arguments
        if len(args) < 1:
            raise EvaluationError("PROMPT() requires at least 1 argument")
        
        prompt_template = str(args[0])
        return_type = str(args[1]) if len(args) > 1 else "str"
        max_tokens = args[2] if len(args) > 2 else None
        
        # Validate return type
        if return_type not in ["str", "int", "float", "bool"]:
            raise EvaluationError(f"PROMPT() return_type must be str, int, float, or bool, got {return_type}")
        
        # Substitute variables in prompt template
        try:
            # Sanitize all variables before substitution
            sanitized_facts = {}
            for key, value in context_facts.items():
                sanitized_facts[key] = self.sanitizer.sanitize_variable(value)
            
            # Substitute variables
            filled_prompt = prompt_template.format(**sanitized_facts)
            
        except KeyError as e:
            raise EvaluationError(f"Missing variable in PROMPT() template: {e}")
        except Exception as e:
            raise EvaluationError(f"Error formatting PROMPT() template: {e}")
        
        # Final prompt sanitization
        safe_prompt = self.sanitizer.sanitize_prompt(filled_prompt)
        
        # Execute LLM call
        try:
            response = self.llm_adapter.complete(
                prompt=safe_prompt,
                max_tokens=max_tokens,
                temperature=self.llm_adapter.config.default_temperature
            )
            
            # Validate and convert response
            converted_value = self.validator.validate_and_convert(
                response.content, 
                return_type
            )
            
            logger.debug(f"PROMPT() call: '{safe_prompt[:100]}...' -> '{response.content}' -> {converted_value}")
            
            return converted_value
            
        except LLMError:
            # Re-raise LLM errors as-is
            raise
        except Exception as e:
            raise LLMError(f"PROMPT() execution failed: {str(e)}") 