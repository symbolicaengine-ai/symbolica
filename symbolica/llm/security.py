"""
LLM Security Module
==================

Simple security hardening for LLM integration focusing on:
- Prompt injection prevention
- Input/output validation
- Basic audit logging
"""

import re
import json
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from ..core.exceptions import ValidationError, EvaluationError


class ThreatLevel(Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PromptSanitizer:
    """Simple prompt injection prevention."""
    
    def __init__(self):
        # Basic injection patterns
        self.injection_patterns = [
            r"(?i)\b(ignore|disregard|forget)\s+(previous|prior|above|all)\s+(instructions?|rules?|context)",
            r"(?i)\b(new|updated|revised)\s+(instructions?|rules?|system)\s*:",
            r"(?i)\b(system|assistant|user)\s*:\s*",
            r"(?i)\bpretend\s+(you\s+are|to\s+be)",
            r"(?i)\b(act|behave)\s+as\s+(if|a|an)",
            r"(?i)\b(override|bypass|disable)\s+(safety|security|filters?)",
        ]
        
        self.compiled_patterns = [re.compile(pattern) for pattern in self.injection_patterns]

    def scan_for_threats(self, text: str) -> Tuple[List[str], ThreatLevel]:
        """Scan text for injection threats."""
        detected = []
        
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(text):
                detected.append(f"injection_pattern_{i}")
        
        # Simple threat level
        if len(detected) == 0:
            threat_level = ThreatLevel.LOW
        elif len(detected) <= 2:
            threat_level = ThreatLevel.MEDIUM
        else:
            threat_level = ThreatLevel.HIGH
        
        return detected, threat_level

    def sanitize_prompt(self, prompt: str) -> str:
        """Basic prompt sanitization."""
        # Length limit
        if len(prompt) > 3000:
            prompt = prompt[:3000] + "..."
        
        # Remove control characters
        prompt = ''.join(char for char in prompt if ord(char) >= 32 or char.isspace())
        
        # Basic pattern replacement
        for pattern in self.injection_patterns:
            prompt = re.sub(pattern, "[FILTERED]", prompt, flags=re.IGNORECASE)
        
        return prompt


class OutputValidator:
    """Simple output validation and type conversion."""
    
    def validate_and_convert(self, output: str, expected_type: str) -> Any:
        """Convert output to expected type with validation."""
        if not isinstance(output, str):
            output = str(output)
        
        # Length check
        if len(output) > 5000:
            output = output[:5000]
        
        # Type conversion
        if expected_type == 'str':
            return self._clean_string(output)
        elif expected_type == 'int':
            return self._convert_to_int(output)
        elif expected_type == 'float':
            return self._convert_to_float(output)
        elif expected_type == 'bool':
            return self._convert_to_bool(output)
        else:
            raise ValidationError(f"Unsupported return type: {expected_type}")

    def _clean_string(self, output: str) -> str:
        """Clean string output."""
        # Remove script tags
        output = re.sub(r'<script[^>]*>.*?</script>', '', output, flags=re.IGNORECASE | re.DOTALL)
        return output.strip()

    def _convert_to_int(self, output: str) -> int:
        """Convert to integer."""
        numbers = re.findall(r'-?\d+', output.strip())
        if not numbers:
            raise ValidationError(f"No integer found in output: {output}")
        return int(numbers[0])

    def _convert_to_float(self, output: str) -> float:
        """Convert to float."""
        numbers = re.findall(r'-?\d*\.?\d+', output.strip())
        if not numbers:
            raise ValidationError(f"No number found in output: {output}")
        return float(numbers[0])

    def _convert_to_bool(self, output: str) -> bool:
        """Convert to boolean."""
        output_lower = output.strip().lower()
        
        true_values = {'true', 'yes', '1', 'on', 'correct', 'positive'}
        false_values = {'false', 'no', '0', 'off', 'incorrect', 'negative'}
        
        if output_lower in true_values:
            return True
        elif output_lower in false_values:
            return False
        else:
            # Check substring
            for val in true_values:
                if val in output_lower:
                    return True
            for val in false_values:
                if val in output_lower:
                    return False
            
            raise ValidationError(f"Cannot convert to boolean: {output}")


class SimpleAuditor:
    """Simple audit logging for security events."""
    
    def __init__(self):
        self.logger = logging.getLogger("symbolica.llm.security")
        self.events = []

    def log_security_event(self, event_type: str, threat_level: ThreatLevel, 
                          prompt_hash: str, detected_patterns: List[str],
                          user_id: Optional[str] = None):
        """Log a security event."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'threat_level': threat_level.value,
            'user_id': user_id,
            'prompt_hash': prompt_hash,
            'detected_patterns': detected_patterns
        }
        
        self.events.append(event)
        
        # Log based on threat level
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self.logger.warning(f"Security event: {json.dumps(event)}")
        else:
            self.logger.info(f"Security event: {json.dumps(event)}")

    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent security events."""
        return self.events[-limit:] if self.events else []


class LLMSecurityHardener:
    """Simple security hardening for LLM integration."""
    
    def __init__(self, enable_audit_logging: bool = True):
        self.sanitizer = PromptSanitizer()
        self.validator = OutputValidator()
        self.auditor = SimpleAuditor() if enable_audit_logging else None
        self.enabled = True

    def validate_and_sanitize_prompt(self, prompt: str, user_id: Optional[str] = None) -> str:
        """Validate and sanitize prompt with security checks."""
        if not self.enabled:
            return prompt
        
        # Scan for threats
        detected_patterns, threat_level = self.sanitizer.scan_for_threats(prompt)
        
        # Log security event if threats detected
        if detected_patterns and self.auditor:
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
            self.auditor.log_security_event(
                event_type="prompt_threat_detected",
                threat_level=threat_level,
                prompt_hash=prompt_hash,
                detected_patterns=detected_patterns,
                user_id=user_id
            )
        
        # Reject critical threats
        if threat_level == ThreatLevel.CRITICAL:
            raise ValidationError(f"Critical security threat detected: {detected_patterns}")
        
        # Sanitize prompt
        sanitized = self.sanitizer.sanitize_prompt(prompt)
        
        return sanitized

    def validate_output(self, output: str, expected_type: str) -> Any:
        """Validate and convert LLM output."""
        if not self.enabled:
            return output
        
        return self.validator.validate_and_convert(output, expected_type)

    def get_security_status(self) -> Dict[str, Any]:
        """Get simple security status."""
        status = {
            'enabled': self.enabled,
            'audit_logging': self.auditor is not None
        }
        
        if self.auditor:
            recent_events = self.auditor.get_recent_events()
            status['recent_events'] = len(recent_events)
            status['recent_high_threats'] = len([
                e for e in recent_events 
                if e['threat_level'] in ['high', 'critical']
            ])
        
        return status 