"""
Safe expression evaluator for rule conditions and actions.

This module provides a secure way to evaluate Python expressions in rules
without allowing arbitrary code execution.

Uses simpleeval library to provide a restricted Python expression evaluator
that blocks dangerous operations like:
- Importing modules
- Accessing __builtins__
- Using eval/exec
- File operations
- System calls

Example:
    >>> from machine_rules.security import safe_eval
    >>> safe_eval("fact.get('value') > 100", {'fact': {'value': 150}})
    True
    
    >>> safe_eval("__import__('os')", {})
    SecurityError: ...
"""

from typing import Any, Dict
import logging

try:
    from simpleeval import EvalWithCompoundTypes, NameNotDefined, FunctionNotDefined, AttributeDoesNotExist  # type: ignore[import-untyped]
    SIMPLEEVAL_AVAILABLE = True
except ImportError:
    SIMPLEEVAL_AVAILABLE = False

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when an expression attempts unsafe operations."""
    pass


def safe_eval(expression: str, names: Dict[str, Any]) -> Any:
    """
    Safely evaluate a Python expression with restricted capabilities.
    
    This function evaluates Python expressions in a sandboxed environment that:
    - Only allows safe operations (arithmetic, comparisons, dict/list access)
    - Blocks imports, eval, exec, and other dangerous functions
    - Blocks access to __builtins__ and dunder methods
    - Provides controlled access to specified variables
    
    Args:
        expression: Python expression string to evaluate
        names: Dictionary of variable names available to the expression
    
    Returns:
        Result of evaluating the expression
    
    Raises:
        SecurityError: If the expression attempts unsafe operations
        ValueError: If the expression is invalid
        
    Example:
        >>> safe_eval("x + y", {'x': 10, 'y': 20})
        30
        
        >>> safe_eval("fact.get('score', 0) > 80", {'fact': {'score': 90}})
        True
    """
    if not SIMPLEEVAL_AVAILABLE:
        logger.error(
            "simpleeval library not available. Install it with: "
            "pip install simpleeval"
        )
        raise ImportError(
            "simpleeval is required for safe expression evaluation. "
            "Install it with: pip install simpleeval"
        )
    
    if not isinstance(expression, str):
        raise ValueError(f"Expression must be a string, got {type(expression)}")
    
    if not expression.strip():
        raise ValueError("Expression cannot be empty")
    
    # Check for obviously dangerous patterns
    dangerous_patterns = [
        '__import__',
        '__builtins__',
        'eval',
        'exec',
        'compile',
        'open',
        '__class__',
        '__base__',
        '__subclasses__',
        '__globals__',
        '__code__',
        'lambda',
    ]
    
    expression_lower = expression.lower()
    for pattern in dangerous_patterns:
        if pattern.lower() in expression_lower:
            raise SecurityError(
                f"Expression contains dangerous pattern: {pattern}"
            )
    
    try:
        # Use EvalWithCompoundTypes to support dict/list/tuple literals
        # This allows expressions like {'key': 'value'} and ['item1', 'item2']
        evaluator = EvalWithCompoundTypes(names=names)
        result = evaluator.eval(expression)
        return result
        
    except (NameNotDefined, FunctionNotDefined, AttributeDoesNotExist) as e:
        # These are simpleeval-specific exceptions
        raise SecurityError(f"Expression uses undefined or unsafe names: {e}")
    
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {e}")
    
    except Exception as e:
        # Catch any other exceptions and wrap in SecurityError
        logger.warning(f"Expression evaluation failed: {e}")
        raise SecurityError(f"Expression evaluation failed: {e}")


def validate_expression(expression: str) -> bool:
    """
    Validate that an expression is safe without evaluating it.
    
    Args:
        expression: Expression string to validate
    
    Returns:
        True if expression appears safe, False otherwise
    """
    try:
        safe_eval(expression, {})
        return True
    except (SecurityError, ValueError):
        return False
    except Exception:
        # If evaluation fails for other reasons (like NameError),
        # it might still be a valid safe expression
        return True
