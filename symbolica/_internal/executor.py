"""
Action Execution
===============

Handles execution of rule actions with extensible action types.
"""

from typing import List, Dict, Any
from ..core import (
    Action, ExecutionContext, ActionExecutor,
    ActionExecutionError
)


class StandardActionExecutor(ActionExecutor):
    """
    Standard action executor supporting common action types.
    
    Supported actions:
    - set: Set facts in the context
    - call: Call functions (future extension)
    - emit: Emit events (future extension)
    """
    
    def __init__(self):
        self._action_handlers = {
            'set': self._handle_set_action,
            'call': self._handle_call_action,
            'emit': self._handle_emit_action,
        }
    
    def execute(self, actions: List[Action], context: ExecutionContext) -> None:
        """Execute list of actions."""
        for action in actions:
            try:
                if action.type in self._action_handlers:
                    self._action_handlers[action.type](action, context)
                else:
                    raise ActionExecutionError(
                        f"Unsupported action type: {action.type}",
                        action_type=action.type
                    )
            except Exception as e:
                if isinstance(e, ActionExecutionError):
                    raise
                raise ActionExecutionError(
                    f"Action execution failed: {e}",
                    action_type=action.type
                ) from e
    
    def supported_action_types(self) -> List[str]:
        """Get list of supported action types."""
        return list(self._action_handlers.keys())
    
    def register_action_handler(self, action_type: str, handler: callable) -> None:
        """Register custom action handler."""
        self._action_handlers[action_type] = handler
    
    def _handle_set_action(self, action: Action, context: ExecutionContext) -> None:
        """Handle set action - sets facts in context."""
        if not isinstance(action.parameters, dict):
            raise ActionExecutionError(
                "Set action parameters must be a dictionary",
                action_type="set"
            )
        
        # Set all key-value pairs in the context
        for key, value in action.parameters.items():
            context.set_fact(key, value)
    
    def _handle_call_action(self, action: Action, context: ExecutionContext) -> None:
        """Handle call action - calls functions (placeholder for future)."""
        # Future implementation could call external functions
        # For now, just log that a call action was requested
        function_name = action.parameters.get('function')
        if function_name:
            # Could implement function registry here
            pass
    
    def _handle_emit_action(self, action: Action, context: ExecutionContext) -> None:
        """Handle emit action - emits events (placeholder for future)."""
        # Future implementation could emit events to external systems
        event_type = action.parameters.get('event')
        if event_type:
            # Could implement event emitter here
            pass 