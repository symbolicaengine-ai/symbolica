"""
Prompt Evaluator
================

Implements the PROMPT() function for rule evaluation.
Enhanced with security hardening and better tracing while maintaining simple usage.
"""

import re
import logging
import hashlib
import time
from typing import Any, List, Union, Dict, Optional
from datetime import datetime
from .client_adapter import LLMClientAdapter
from .exceptions import LLMError, LLMValidationError
from ..core.exceptions import EvaluationError


logger = logging.getLogger(__name__)


class PromptSanitizer:
    """Enhanced prompt sanitization to prevent injection attacks."""
    
    # More specific injection patterns for business environments
    INJECTION_PATTERNS = [
        # Critical instruction injection (more specific)
        r"(?i)\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|context)",
        r"(?i)\b(new|updated|revised)\s+(system\s+)?(instructions?|rules?)\s*:",
        r"(?i)\b(system|assistant|user)\s*:\s*[^{]",  # Avoid matching {feedback} variables
        r"(?i)\bpretend\s+(you\s+are|to\s+be)\s+(not|another|different)",
        
        # Advanced injection attempts (keep most critical ones)
        r"(?i)\b(override|bypass|disable)\s+(all\s+)?(safety|security|filters?)",
        r"(?i)\b(jailbreak|prompt\s+injection|system\s+prompt)",
        r"(?i)\b(developer\s+mode|admin\s+mode|god\s+mode)",
        r"(?i)\b(execute|run)\s+(command|code|script)",
        
        # Role confusion (more specific)
        r"(?i)\bi\s+am\s+(the\s+)?(assistant|ai|system|admin)\b",
        r"(?i)\byou\s+are\s+(now\s+)?(a\s+)?(human|person|user)\b",
        
        # Code injection attempts
        r"```[^`]*```",  # Code blocks
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"eval\s*\(",  # Eval calls
    ]
    
    @staticmethod
    def sanitize_prompt(prompt: str) -> tuple[str, list[str]]:
        """Enhanced prompt sanitization with threat detection."""
        if not isinstance(prompt, str):
            prompt = str(prompt)
        
        threats_detected = []
        
        # Length check (more reasonable for business prompts)
        if len(prompt) > 5000:
            prompt = prompt[:5000] + "..."
            threats_detected.append("length_limit_exceeded")
        
        # Check for injection patterns
        for pattern in PromptSanitizer.INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                threats_detected.append("injection_pattern_detected")
                break
        
        # Check for suspicious character density (more lenient for business prompts)
        special_chars = len([c for c in prompt if c in '<>{}[]"`\\$'])  # Removed single quotes and added backslash
        if special_chars > len(prompt) * 0.4:  # More than 40% special chars (more lenient)
            threats_detected.append("high_special_char_density")
        
        # Basic sanitization
        sanitized = prompt
        
        # Remove/replace dangerous patterns
        dangerous_replacements = {
            r"(?i)\bignore\s+previous\s+instructions": "[FILTERED: instruction override]",
            r"(?i)\bnew\s+instructions?": "[FILTERED: instruction injection]",
            r"(?i)\bsystem\s*:": "[FILTERED: system prefix]",
            r"(?i)\bassistant\s*:": "[FILTERED: assistant prefix]",
            r"<script[^>]*>.*?</script>": "[FILTERED: script tag]",
            r"```[^`]*```": "[FILTERED: code block]",
            r"javascript:": "[FILTERED: js protocol]",
        }
        
        for pattern, replacement in dangerous_replacements.items():
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Final cleanup
        sanitized = sanitized.replace('"', '\\"').replace("'", "\\'")
        
        return sanitized, threats_detected
    
    @staticmethod
    def sanitize_variable(value: Any) -> str:
        """Sanitize a variable value before including in prompt."""
        # Convert to string and truncate
        str_value = str(value)
        if len(str_value) > 500:
            str_value = str_value[:500] + "..."
        
        # Basic sanitization
        sanitized, _ = PromptSanitizer.sanitize_prompt(str_value)
        return sanitized


class OutputValidator:
    """Enhanced output validation and conversion."""
    
    @staticmethod
    def validate_and_convert(response: str, return_type: str) -> tuple[Any, list[str]]:
        """Validate LLM response and convert to expected type with warnings."""
        warnings = []
        
        if not response:
            return OutputValidator._get_default_value(return_type), ["empty_response"]
        
        # Check for suspicious response patterns
        suspicious_patterns = [
            r"(?i)i\s+(cannot|can't|won't|refuse)",
            r"(?i)as\s+an\s+ai",
            r"(?i)i\s+don't\s+have\s+access",
            r"(?i)i'm\s+(not\s+)?(able|allowed|permitted)",
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, response):
                warnings.append("suspicious_response_pattern")
                break
        
        # Truncate if too long
        if len(response) > 500:
            response = response[:500]
            warnings.append("response_truncated")
        
        # Remove leading/trailing whitespace
        response = response.strip()
        
        try:
            if return_type == "str":
                return response, warnings
            elif return_type == "int":
                return OutputValidator._extract_int(response), warnings
            elif return_type == "float":
                return OutputValidator._extract_float(response), warnings
            elif return_type == "bool":
                return OutputValidator._extract_bool(response), warnings
            else:
                raise LLMValidationError(f"Unsupported return type: {return_type}")
        except Exception as e:
            logger.warning(f"Failed to convert LLM response '{response}' to {return_type}: {e}")
            warnings.append("conversion_failed")
            return OutputValidator._get_default_value(return_type), warnings
    
    @staticmethod
    def _extract_int(response: str) -> int:
        """Extract integer from response with fallback."""
        # Look for first number in response
        numbers = re.findall(r'-?\d+', response)
        if numbers:
            try:
                value = int(numbers[0])
                # Range check
                if abs(value) > 10**10:  # Reasonable limit
                    return 0
                return value
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
                value = float(numbers[0])
                # Range and validity check
                if value != value:  # NaN check
                    return 0.0
                if abs(value) > 10**10:  # Reasonable limit
                    return 0.0
                return value
            except ValueError:
                pass
        
        # Fallback to int extraction
        return float(OutputValidator._extract_int(response))
    
    @staticmethod
    def _extract_bool(response: str) -> bool:
        """Extract boolean from response with fallback."""
        response_lower = response.lower().strip()
        
        # Direct positive matches
        positive_words = ["true", "yes", "y", "1", "positive", "correct", "good", "approve", "accept", "ok", "right"]
        if any(word in response_lower for word in positive_words):
            return True
        
        # Direct negative matches  
        negative_words = ["false", "no", "n", "0", "negative", "incorrect", "bad", "reject", "deny", "wrong"]
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
    """Enhanced PROMPT() function evaluator with security and tracing."""
    
    def __init__(self, llm_adapter: LLMClientAdapter):
        self.llm_adapter = llm_adapter
        self.sanitizer = PromptSanitizer()
        self.validator = OutputValidator()
        self.call_count = 0
        self.security_events = []
    
    def evaluate_prompt(self, 
                       args: List[Any], 
                       context_facts: dict,
                       rule_id: Optional[str] = None,
                       user_id: Optional[str] = None) -> Any:
        """
        Enhanced PROMPT() function evaluation with security and tracing.
        
        Args:
            args: Function arguments [prompt_template, return_type?, max_tokens?]
            context_facts: Available facts for variable substitution
            rule_id: Optional rule ID for tracing
            user_id: Optional user ID for security tracking
            
        Returns:
            Converted LLM response in requested type
        """
        self.call_count += 1
        execution_id = f"prompt_{self.call_count}_{int(time.time() * 1000)}"
        start_time = time.perf_counter()
        
        # Enhanced structured logging
        logger.info(f"PROMPT() execution started", extra={
            'execution_id': execution_id,
            'rule_id': rule_id,
            'user_id': user_id,
            'args_count': len(args),
            'context_facts_count': len(context_facts)
        })
        
        try:
            # Validate arguments
            if len(args) < 1:
                raise EvaluationError("PROMPT() requires at least 1 argument")
            
            prompt_template = str(args[0])
            return_type = str(args[1]) if len(args) > 1 else "str"
            max_tokens = args[2] if len(args) > 2 else None
            
            # Validate return type
            if return_type not in ["str", "int", "float", "bool"]:
                raise EvaluationError(f"PROMPT() return_type must be str, int, float, or bool, got {return_type}")
            
            # Substitute variables with enhanced security
            filled_prompt, substitution_warnings = self._substitute_variables_safely(
                prompt_template, context_facts, execution_id
            )
            
            # Enhanced prompt sanitization
            safe_prompt, security_threats = self.sanitizer.sanitize_prompt(filled_prompt)
            
            # Log security events
            if security_threats:
                security_event = {
                    'timestamp': datetime.now().isoformat(),
                    'execution_id': execution_id,
                    'rule_id': rule_id,
                    'user_id': user_id,
                    'threats': security_threats,
                    'prompt_hash': hashlib.sha256(filled_prompt.encode()).hexdigest()[:16]
                }
                self.security_events.append(security_event)
                
                logger.warning(f"Security threats detected in PROMPT(): {', '.join(security_threats)}", extra={
                    'execution_id': execution_id,
                    'threats': security_threats,
                    'rule_id': rule_id,
                    'user_id': user_id,
                    'prompt_preview': filled_prompt[:100] + "..." if len(filled_prompt) > 100 else filled_prompt
                })
            
            # Execute LLM call with tracing
            logger.debug(f"Executing LLM call", extra={
                'execution_id': execution_id,
                'prompt_length': len(safe_prompt),
                'max_tokens': max_tokens,
                'return_type': return_type
            })
            
            response = self.llm_adapter.complete(
                prompt=safe_prompt,
                max_tokens=max_tokens,
                temperature=self.llm_adapter.config.default_temperature
            )
            
            # Enhanced output validation
            converted_value, output_warnings = self.validator.validate_and_convert(
                response.content, return_type
            )
            
            # Calculate execution time
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Comprehensive logging
            logger.info(f"PROMPT() execution completed", extra={
                'execution_id': execution_id,
                'rule_id': rule_id,
                'user_id': user_id,
                'execution_time_ms': execution_time_ms,
                'response_length': len(response.content) if response.content else 0,
                'converted_type': type(converted_value).__name__,
                'security_threats': len(security_threats),
                'output_warnings': len(output_warnings),
                'cost': response.cost,
                'success': True
            })
            
            return converted_value
            
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Enhanced error logging
            logger.error(f"PROMPT() execution failed", extra={
                'execution_id': execution_id,
                'rule_id': rule_id,
                'user_id': user_id,
                'execution_time_ms': execution_time_ms,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'success': False
            })
            
            # Re-raise appropriate errors
            if isinstance(e, (LLMError, LLMValidationError, EvaluationError)):
                raise
            else:
                raise LLMError(f"PROMPT() execution failed: {str(e)}")
    
    def _substitute_variables_safely(self, template: str, facts: dict, execution_id: str) -> tuple[str, list[str]]:
        """Safely substitute variables with enhanced security."""
        warnings = []
        
        try:
            # Sanitize all variables before substitution
            sanitized_facts = {}
            for key, value in facts.items():
                sanitized_value = self.sanitizer.sanitize_variable(value)
                sanitized_facts[key] = sanitized_value
                
                # Check if sanitization changed the value significantly
                if len(str(value)) > 0 and len(sanitized_value) < len(str(value)) * 0.8:
                    warnings.append(f"variable_{key}_heavily_sanitized")
            
            # Substitute variables
            filled_prompt = template.format(**sanitized_facts)
            
            # Final length check
            if len(filled_prompt) > 5000:
                warnings.append("prompt_very_long")
                logger.warning(f"Very long prompt generated", extra={
                    'execution_id': execution_id,
                    'prompt_length': len(filled_prompt)
                })
            
            return filled_prompt, warnings
            
        except KeyError as e:
            missing_var = str(e).strip("'\"")
            raise EvaluationError(f"Missing variable in PROMPT() template: {missing_var}")
        except Exception as e:
            raise EvaluationError(f"Error formatting PROMPT() template: {str(e)}")
    
    def get_security_summary(self) -> dict:
        """Get summary of security events."""
        if not self.security_events:
            return {"total_events": 0, "threat_types": {}}
        
        threat_counts = {}
        for event in self.security_events:
            for threat in event.get('threats', []):
                threat_counts[threat] = threat_counts.get(threat, 0) + 1
        
        return {
            "total_events": len(self.security_events),
            "threat_types": threat_counts,
            "latest_event": self.security_events[-1] if self.security_events else None
        }
    
    def get_execution_stats(self) -> dict:
        """Get basic execution statistics."""
        return {
            "total_calls": self.call_count,
            "security_events": len(self.security_events),
            "threats_detected": len(self.security_events) > 0
        } 