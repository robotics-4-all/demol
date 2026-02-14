"""
Core Validation Infrastructure for DeMoL

This module provides the core validation infrastructure including:
- Validation state management
- Error and warning collection
- Validation result reporting
"""

from textx import get_location, TextXSemanticError
import warnings

# Global lists to collect validation results during a single model processing run
_validation_errors = []
_validation_warnings = []
_passed_rules = []


def clear_validation_results():
    """Clear the collected validation results."""
    global _validation_errors, _validation_warnings, _passed_rules
    _validation_errors = []
    _validation_warnings = []
    _passed_rules = []


def get_validation_errors():
    """Get the list of collected validation errors."""
    return _validation_errors


def get_validation_warnings():
    """Get the list of collected validation warnings."""
    return _validation_warnings


def get_passed_rules():
    """Get the list of passed validation rules."""
    return _passed_rules


def report_passed_rule(rule_name: str, description: str = ""):
    """Record that a validation rule has passed successfully."""
    _passed_rules.append({"name": rule_name, "description": description})


class ValidationError(TextXSemanticError):
    """Custom validation error with location information."""

    pass


def raise_validation_error(obj, msg: str, error_type: str = "Semantics"):
    """Collect a validation error with location information without terminating immediately."""
    loc = get_location(obj)

    # Format the error message
    error_msg = f"[{error_type}] {msg}"

    _validation_errors.append({"obj": obj, "msg": error_msg, "loc": loc, "type": error_type})


def raise_validation_warning(obj, msg: str, warning_type: str = "Warning"):
    """Collect a validation warning with location information."""
    loc = get_location(obj)

    # Format the warning message
    warning_msg = f"[{warning_type}] {msg}"

    _validation_warnings.append({"obj": obj, "msg": warning_msg, "loc": loc, "type": warning_type})

    # Emit actual Python warning for tests/users
    warnings.warn(warning_msg, UserWarning)


def check_validation_errors(model, skip_semantics=False):
    """Check if any validation errors occurred and raise a single exception if they did."""
    if _validation_errors and not skip_semantics:
        # Raise the first error to stop further processing and allow tests to match the message
        first_error = _validation_errors[0]["msg"]
        raise ValidationError(first_error)
