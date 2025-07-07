"""
Simple Action Executor
======================

Fast action executor for AI agent rule processing.
"""

from typing import Dict, Any, TYPE_CHECKING

from ..core.interfaces import ActionExecutor

if TYPE_CHECKING:
    from ..core.models import ExecutionContext


class SimpleActionExecutor(ActionExecutor):
    """Simple action executor that sets key-value pairs."""
    
    def execute(self, actions: Dict[str, Any], context: 'ExecutionContext') -> None:
        """Execute actions by setting facts in the context."""
        for key, value in actions.items():
            context.set_fact(key, value)


def create_executor() -> SimpleActionExecutor:
    """Factory function to create simple action executor."""
    return SimpleActionExecutor() 