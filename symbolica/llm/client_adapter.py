"""
LLM Client Adapter
==================

Simple adapter to normalize different LLM clients to a common interface.
Supports OpenAI and Anthropic clients.
"""

import time
from dataclasses import dataclass
from typing import Any, Optional
from .config import LLMConfig
from .exceptions import LLMError, LLMTimeoutError, LLMValidationError


@dataclass
class LLMResponse:
    """Simple response from LLM call."""
    content: str
    cost: float
    latency_ms: float


class LLMClientAdapter:
    """Adapts different LLM clients to a common interface."""
    
    def __init__(self, client: Any, config: Optional[LLMConfig] = None):
        self.client = client
        self.config = config or LLMConfig.defaults()
        self.client_type = self._detect_client_type(client)
        self.total_cost = 0.0
    
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
                 temperature: Optional[float] = None) -> LLMResponse:
        """Complete a prompt using the configured LLM client."""
        
        # Check cost limits
        if self.total_cost >= self.config.max_cost_per_execution:
            raise LLMError(f"Cost limit exceeded: ${self.total_cost:.4f}")
        
        # Use config defaults if not specified
        max_tokens = max_tokens or self.config.default_max_tokens
        temperature = temperature or self.config.default_temperature
        
        start_time = time.perf_counter()
        
        try:
            if self.client_type == 'openai':
                response = self._call_openai(prompt, max_tokens, temperature)
            elif self.client_type == 'anthropic':
                response = self._call_anthropic(prompt, max_tokens, temperature)
            else:
                raise LLMError(f"Unsupported client type: {self.client_type}")
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Simple cost estimation (rough approximation)
            estimated_cost = self._estimate_cost(prompt, response.content, max_tokens)
            self.total_cost += estimated_cost
            
            llmResponse = LLMResponse(
                content=response.content,
                cost=estimated_cost,
                latency_ms=latency_ms
            )
            print(llmResponse)
            return llmResponse
            
        except Exception as e:
            if 'timeout' in str(e).lower():
                raise LLMTimeoutError(f"LLM call timed out: {e}")
            else:
                raise LLMError(f"LLM call failed: {e}")
    
    def _call_openai(self, prompt: str, max_tokens: int, temperature: float) -> Any:
        """Call OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Default model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.config.timeout_seconds
            )
            return response.choices[0].message
        except Exception as e:
            raise LLMError(f"OpenAI API call failed: {e}")
    
    def _call_anthropic(self, prompt: str, max_tokens: int, temperature: float) -> Any:
        """Call Anthropic API."""
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Default model
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.config.timeout_seconds
            )
            return response.content[0]
        except Exception as e:
            raise LLMError(f"Anthropic API call failed: {e}")
    
    def _estimate_cost(self, prompt: str, response: str, max_tokens: int) -> float:
        """Simple cost estimation (very rough approximation)."""
        # Rough estimation: $0.0015 per 1K tokens for input, $0.002 per 1K tokens for output
        input_tokens = len(prompt) // 4  # Rough approximation: 1 token ≈ 4 characters
        output_tokens = len(response) // 4
        
        input_cost = (input_tokens / 1000) * 0.0015
        output_cost = (output_tokens / 1000) * 0.002
        
        return input_cost + output_cost 