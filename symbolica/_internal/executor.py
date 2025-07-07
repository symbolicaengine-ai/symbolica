"""
Simple Action Executor
======================

Simple action execution for AI agent reasoning.
Only supports basic key-value setting actions.
"""

from typing import Dict, Any
from ..core import ExecutionContext, ActionExecutor


class SimpleActionExecutor(ActionExecutor):
    """Simple action executor for setting key-value pairs in context."""
    
    def execute(self, actions: Dict[str, Any], context: ExecutionContext) -> None:
        """Execute actions by setting key-value pairs in context."""
        for key, value in actions.items():
            context.set_fact(key, value)


# Factory function
def create_executor() -> SimpleActionExecutor:
    """Create simple action executor."""
    return SimpleActionExecutor() 