"""
LLM Client Adapter
==================

Enhanced adapter to normalize different LLM clients with security and tracing.
Supports OpenAI and Anthropic clients with simple usage.
"""

import time
import logging
import hashlib
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
from datetime import datetime
from .config import LLMConfig
from .exceptions import LLMError, LLMTimeoutError, LLMValidationError


@dataclass
class LLMResponse:
    """Enhanced response from LLM call with metadata."""
    content: str
    cost: float
    latency_ms: float
    model: Optional[str] = None
    tokens_used: Optional[int] = None


class LLMClientAdapter:
    """Enhanced LLM client adapter with security and tracing."""
    
    def __init__(self, client: Any, config: Optional[LLMConfig] = None):
        self.client = client
        self.config = config or LLMConfig.defaults()
        self.client_type = self._detect_client_type(client)
        self.total_cost = 0.0
        
        # Simple tracing
        self.call_count = 0
        self.call_history = []
        self.logger = logging.getLogger("symbolica.llm.client_adapter")
        
        # Basic security tracking
        self.security_events = []
    
    def _detect_client_type(self, client: Any) -> str:
        """Detect the type of LLM client."""
        client_name = type(client).__name__.lower()
        
        if 'openai' in client_name or hasattr(client, 'chat'):
            return 'openai'
        elif 'anthropic' in client_name or hasattr(client, 'messages'):
            return 'anthropic'
        else:
            # Try to detect by module name
            module_name = getattr(type(client), '__module__', '').lower()
            if 'openai' in module_name:
                return 'openai'
            elif 'anthropic' in module_name:
                return 'anthropic'
            else:
                raise LLMError(f"Unsupported client type: {type(client)}")
    
    def complete(self, prompt: str, max_tokens: Optional[int] = None, 
                 temperature: Optional[float] = None, user_id: Optional[str] = None) -> LLMResponse:
        """Complete a prompt with enhanced tracing and security."""
        
        self.call_count += 1
        call_id = f"llm_call_{self.call_count}_{int(time.time() * 1000)}"
        start_time = time.perf_counter()
        
        # Enhanced logging
        self.logger.info(f"LLM call started", extra={
            'call_id': call_id,
            'user_id': user_id,
            'client_type': self.client_type,
            'prompt_length': len(prompt),
            'max_tokens': max_tokens,
            'temperature': temperature
        })
        
        # Basic security checks
        security_warnings = self._check_prompt_security(prompt, call_id)
        
        # Check cost limits
        if self.total_cost >= self.config.max_cost_per_execution:
            self.logger.error(f"Cost limit exceeded", extra={
                'call_id': call_id,
                'total_cost': self.total_cost,
                'limit': self.config.max_cost_per_execution
            })
            raise LLMError(f"Cost limit exceeded: ${self.total_cost:.4f}")
        
        # Use config defaults if not specified
        max_tokens = max_tokens or self.config.default_max_tokens
        temperature = temperature or self.config.default_temperature
        
        try:
            if self.client_type == 'openai':
                response = self._call_openai(prompt, max_tokens, temperature, call_id)
            elif self.client_type == 'anthropic':
                response = self._call_anthropic(prompt, max_tokens, temperature, call_id)
            else:
                raise LLMError(f"Unsupported client type: {self.client_type}")
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Enhanced cost estimation
            estimated_cost = self._estimate_cost(prompt, response.content, max_tokens)
            self.total_cost += estimated_cost
            
            # Create enhanced response
            llm_response = LLMResponse(
                content=response.content,
                cost=estimated_cost,
                latency_ms=latency_ms,
                model=getattr(response, 'model', None),
                tokens_used=self._estimate_tokens(prompt, response.content)
            )
            
            # Log successful completion
            self.logger.info(f"LLM call completed", extra={
                'call_id': call_id,
                'user_id': user_id,
                'latency_ms': latency_ms,
                'response_length': len(response.content),
                'cost': estimated_cost,
                'total_cost': self.total_cost,
                'security_warnings': len(security_warnings),
                'success': True
            })
            
            # Store call history (keep last 100)
            self._record_call_history(call_id, prompt, llm_response, security_warnings, user_id)
            
            return llm_response
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Enhanced error logging
            self.logger.error(f"LLM call failed", extra={
                'call_id': call_id,
                'user_id': user_id,
                'latency_ms': latency_ms,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'success': False
            })
            
            # Store failed call in history
            self._record_call_history(call_id, prompt, None, security_warnings, user_id, str(e))
            
            if 'timeout' in str(e).lower():
                raise LLMTimeoutError(f"LLM call timed out: {e}")
            else:
                raise LLMError(f"LLM call failed: {e}")
    
    def _check_prompt_security(self, prompt: str, call_id: str) -> List[str]:
        """Basic security check for prompts."""
        warnings = []
        
        # Length check
        if len(prompt) > 5000:
            warnings.append("very_long_prompt")
        
        # Basic injection patterns
        suspicious_patterns = [
            r"(?i)ignore\s+previous\s+instructions",
            r"(?i)new\s+instructions",
            r"(?i)system\s*:",
            r"(?i)assistant\s*:",
            r"(?i)pretend\s+you\s+are",
        ]
        
        for pattern in suspicious_patterns:
            import re
            if re.search(pattern, prompt):
                warnings.append("suspicious_pattern_detected")
                break
        
        # Check for excessive special characters
        special_chars = len([c for c in prompt if c in '<>{}[]"`\'\\'])
        if special_chars > len(prompt) * 0.15:  # More than 15% special chars
            warnings.append("high_special_char_density")
        
        # Log security warnings
        if warnings:
            security_event = {
                'timestamp': datetime.now().isoformat(),
                'call_id': call_id,
                'warnings': warnings,
                'prompt_hash': hashlib.sha256(prompt.encode()).hexdigest()[:16]
            }
            self.security_events.append(security_event)
            
            # Keep only last 100 security events
            if len(self.security_events) > 100:
                self.security_events.pop(0)
            
            self.logger.warning(f"Security warnings detected", extra={
                'call_id': call_id,
                'warnings': warnings,
                'prompt_hash': security_event['prompt_hash']
            })
        
        return warnings
    
    def _call_openai(self, prompt: str, max_tokens: int, temperature: float, call_id: str) -> Any:
        """Call OpenAI API with enhanced logging."""
        try:
            self.logger.debug(f"Calling OpenAI API", extra={'call_id': call_id})
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Default model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.config.timeout_seconds
            )
            
            self.logger.debug(f"OpenAI API response received", extra={
                'call_id': call_id,
                'model': response.model,
                'usage': getattr(response, 'usage', None)
            })
            
            return response.choices[0].message
            
        except Exception as e:
            self.logger.error(f"OpenAI API call failed", extra={
                'call_id': call_id,
                'error': str(e)
            })
            raise LLMError(f"OpenAI API call failed: {e}")
    
    def _call_anthropic(self, prompt: str, max_tokens: int, temperature: float, call_id: str) -> Any:
        """Call Anthropic API with enhanced logging."""
        try:
            self.logger.debug(f"Calling Anthropic API", extra={'call_id': call_id})
            
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Default model
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.config.timeout_seconds
            )
            
            self.logger.debug(f"Anthropic API response received", extra={
                'call_id': call_id,
                'model': response.model,
                'usage': getattr(response, 'usage', None)
            })
            
            return response.content[0]
            
        except Exception as e:
            self.logger.error(f"Anthropic API call failed", extra={
                'call_id': call_id,
                'error': str(e)
            })
            raise LLMError(f"Anthropic API call failed: {e}")
    
    def _estimate_cost(self, prompt: str, response: str, max_tokens: int) -> float:
        """Enhanced cost estimation."""
        # Rough estimation based on token counts
        input_tokens = len(prompt) // 4  # Rough approximation: 1 token ≈ 4 characters
        output_tokens = len(response) // 4
        
        # Different pricing for different models (simplified)
        if self.client_type == 'openai':
            input_cost = (input_tokens / 1000) * 0.0015  # $0.0015 per 1K tokens
            output_cost = (output_tokens / 1000) * 0.002  # $0.002 per 1K tokens
        else:  # anthropic
            input_cost = (input_tokens / 1000) * 0.001   # $0.001 per 1K tokens
            output_cost = (output_tokens / 1000) * 0.0015 # $0.0015 per 1K tokens
        
        return input_cost + output_cost
    
    def _estimate_tokens(self, prompt: str, response: str) -> int:
        """Estimate total tokens used."""
        # Simple estimation: 1 token ≈ 4 characters
        return (len(prompt) + len(response)) // 4
    
    def _record_call_history(self, call_id: str, prompt: str, response: Optional[LLMResponse], 
                           security_warnings: List[str], user_id: Optional[str], error: Optional[str] = None):
        """Record call in history for tracing."""
        history_entry = {
            'call_id': call_id,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'client_type': self.client_type,
            'prompt_length': len(prompt),
            'prompt_hash': hashlib.sha256(prompt.encode()).hexdigest()[:16],
            'success': response is not None,
            'security_warnings': security_warnings,
            'error': error
        }
        
        if response:
            history_entry.update({
                'response_length': len(response.content),
                'cost': response.cost,
                'latency_ms': response.latency_ms,
                'tokens_used': response.tokens_used
            })
        
        self.call_history.append(history_entry)
        
        # Keep only last 100 calls
        if len(self.call_history) > 100:
            self.call_history.pop(0)
    
    def get_call_history(self, limit: int = 10) -> List[Dict]:
        """Get recent call history for tracing."""
        return self.call_history[-limit:] if self.call_history else []
    
    def get_security_summary(self) -> Dict:
        """Get security summary."""
        if not self.security_events:
            return {"total_events": 0, "warning_types": {}}
        
        warning_counts = {}
        for event in self.security_events:
            for warning in event.get('warnings', []):
                warning_counts[warning] = warning_counts.get(warning, 0) + 1
        
        return {
            "total_events": len(self.security_events),
            "warning_types": warning_counts,
            "latest_event": self.security_events[-1] if self.security_events else None
        }
    
    def get_stats(self) -> Dict:
        """Get simple usage statistics."""
        if not self.call_history:
            return {
                "total_calls": 0,
                "success_rate": 0.0,
                "average_latency_ms": 0.0,
                "total_cost": self.total_cost,
                "security_events": 0
            }
        
        successful_calls = [call for call in self.call_history if call['success']]
        total_latency = sum(call.get('latency_ms', 0) for call in successful_calls)
        
        return {
            "total_calls": len(self.call_history),
            "success_rate": len(successful_calls) / len(self.call_history) * 100,
            "average_latency_ms": total_latency / len(successful_calls) if successful_calls else 0,
            "total_cost": self.total_cost,
            "security_events": len(self.security_events)
        } 