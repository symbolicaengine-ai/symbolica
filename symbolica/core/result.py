"""
symbolica.result
===============

Result objects for reasoning decisions.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


class Result:
    """Result object for reasoning decisions."""
    
    def __init__(self, 
                 verdict: Dict[str, Any], 
                 trace: Dict[str, Any], 
                 context: Optional[str] = None,
                 rules_file: Optional[str] = None):
        self.verdict = verdict
        self.trace = trace
        self.context = context or "reasoning"
        self.rules_file = rules_file
        self.timestamp = datetime.utcnow().isoformat()
        self.request_id = str(uuid.uuid4())[:8]
    
    @property
    def status(self) -> Optional[str]:
        """Primary decision status."""
        return self.verdict.get("decision_status")
    
    @property
    def reason(self) -> Optional[str]:
        """Primary reason for decision."""
        return self.verdict.get("reason")
    
    @property
    def rules_fired(self) -> List[str]:
        """Rules that fired during reasoning."""
        fired = self.trace.get("fired", [])
        if isinstance(fired, list) and fired and isinstance(fired[0], str):
            return fired  # compact format
        elif isinstance(fired, list):
            return [rule.get("id", "unknown") for rule in fired]  # verbose format
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "context": self.context,
            "rules_file": self.rules_file,
            "status": self.status,
            "reason": self.reason,
            "rules_fired": self.rules_fired,
            "verdict": self.verdict,
            "trace": self.trace
        }
    
    def __repr__(self) -> str:
        return f"Result(id={self.request_id}, status={self.status}, rules={self.rules_file})" 