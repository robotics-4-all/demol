"""User-defined constraint validator.

Rules:
- [Constraint-Violated]: A user-defined CONSTRAINT expression evaluated to false.
- [Constraint-Eval-Error]: A constraint expression could not be evaluated
  (e.g., referencing a non-existent peripheral or attribute).

Constraint expressions support:
- Comparison operators: <, >, <=, >=, ==, !=
- Arithmetic operators: +, -, *, /
- Built-in functions: count(SENSOR|ACTUATOR|PERIPHERAL|CONNECTION),
  sum_power(PERIPHERAL), avg_power(PERIPHERAL), max_power(PERIPHERAL)
- Property access: PeripheralName.attribute_name
- Literals: numbers (with optional unit), strings, booleans
"""

import logging
from ..core import raise_validation_error, raise_validation_warning
from .base import BaseValidator

logger = logging.getLogger(__name__)


# ========================================================================
# Power unit normalization (to mW)
# ========================================================================

_POWER_UNIT_TO_MW = {
    "w": 1000.0,
    "mw": 1.0,
    "uw": 0.001,
}

_CAPACITY_UNIT_TO_MAH = {
    "mah": 1.0,
    "ah": 1000.0,
}

_CURRENT_UNIT_TO_MA = {
    "a": 1000.0,
    "ma": 1.0,
    "ua": 0.001,
}

_FREQ_UNIT_TO_HZ = {
    "ghz": 1e9,
    "mhz": 1e6,
    "khz": 1e3,
    "hz": 1.0,
}


def _normalize_value_with_unit(value, unit):
    """Normalize a numeric value with a unit to its base unit (mW, mA, mAh, Hz).

    Returns the normalized value, or the raw value if no unit is given.
    """
    if unit is None:
        return float(value)

    unit_lower = str(unit).lower()

    if unit_lower in _POWER_UNIT_TO_MW:
        return float(value) * _POWER_UNIT_TO_MW[unit_lower]
    if unit_lower in _CAPACITY_UNIT_TO_MAH:
        return float(value) * _CAPACITY_UNIT_TO_MAH[unit_lower]
    if unit_lower in _CURRENT_UNIT_TO_MA:
        return float(value) * _CURRENT_UNIT_TO_MA[unit_lower]
    if unit_lower in _FREQ_UNIT_TO_HZ:
        return float(value) * _FREQ_UNIT_TO_HZ[unit_lower]

    return float(value)


def _parse_power_mw(power_consumption):
    """Parse a PowerConsumption object to milliwatts."""
    if power_consumption is None:
        return None

    value = getattr(power_consumption, "value", None)
    unit = getattr(power_consumption, "unit", None)

    if value is None or unit is None:
        return None

    return _normalize_value_with_unit(value, unit)


# ========================================================================
# Model introspection helpers
# ========================================================================


def _get_peripherals_by_kind(model, kind):
    """Get peripherals filtered by kind: SENSOR, ACTUATOR, or PERIPHERAL (all)."""
    peripherals = getattr(model.components, "peripherals", [])
    if kind == "PERIPHERAL":
        return peripherals

    result = []
    for p in peripherals:
        ref = p.ref if hasattr(p, "ref") else p
        ref_class = type(ref).__name__
        if kind == "SENSOR" and ref_class == "Sensor":
            result.append(p)
        elif kind == "ACTUATOR" and ref_class == "Actuator":
            result.append(p)
    return result


def _get_peripheral_by_name(model, name):
    """Find a peripheral ComponentInstance by its user-assigned name."""
    peripherals = getattr(model.components, "peripherals", [])
    for p in peripherals:
        p_name = getattr(p, "name", None)
        if p_name == name:
            return p
        ref = p.ref if hasattr(p, "ref") else p
        if ref.name == name:
            return p
    return None


def _get_attribute_value(comp_instance, attr_name):
    """Get a user-defined attribute value from a ComponentInstance's WITH clause."""
    attrs = getattr(comp_instance, "attributes", [])
    for attr in attrs:
        if attr.name == attr_name:
            return attr.value
    return None


# ========================================================================
# Built-in function evaluation
# ========================================================================


def _eval_builtin_func(func_name, arg, model):
    """Evaluate a built-in function against the model.

    Supported functions:
    - count(SENSOR|ACTUATOR|PERIPHERAL|CONNECTION): count of items
    - sum_power(SENSOR|ACTUATOR|PERIPHERAL): sum of power.max in mW
    - avg_power(SENSOR|ACTUATOR|PERIPHERAL): average of power.max in mW
    - max_power(SENSOR|ACTUATOR|PERIPHERAL): maximum power.max in mW
    """
    if func_name == "count":
        if arg == "CONNECTION":
            return float(len(getattr(model, "connections", [])))
        return float(len(_get_peripherals_by_kind(model, arg)))

    if func_name in ("sum_power", "avg_power", "max_power"):
        peripherals = _get_peripherals_by_kind(model, arg)
        power_values = []
        for p in peripherals:
            ref = p.ref if hasattr(p, "ref") else p
            op = getattr(ref, "operational", None)
            if op is None:
                continue
            p_max = _parse_power_mw(getattr(op, "max", None))
            if p_max is not None:
                power_values.append(p_max)

        if not power_values:
            return 0.0

        if func_name == "sum_power":
            return sum(power_values)
        elif func_name == "avg_power":
            return sum(power_values) / len(power_values)
        elif func_name == "max_power":
            return max(power_values)

    raise ValueError(f"Unknown built-in function: {func_name}")


# ========================================================================
# Expression evaluator (recursive AST walker)
# ========================================================================


class ConstraintEvalError(Exception):
    """Raised when a constraint expression cannot be evaluated."""

    pass


def _eval_atom(atom, model):
    """Evaluate an AtomExpr node."""
    cls_name = type(atom).__name__

    if cls_name == "FunctionCallExpr":
        return _eval_builtin_func(atom.func, atom.arg, model)

    if cls_name == "NumberLiteral":
        return _normalize_value_with_unit(atom.value, atom.unit)

    if cls_name == "StringLiteral":
        return atom.value

    if cls_name == "BoolLiteral":
        return atom.value

    if cls_name == "PropertyAccessExpr":
        segments = atom.segments
        if not segments:
            raise ConstraintEvalError("Empty property access")

        # First segment is the peripheral name
        periph_name = segments[0]
        periph = _get_peripheral_by_name(model, periph_name)
        if periph is None:
            raise ConstraintEvalError(
                f"Unknown peripheral '{periph_name}'. "
                f"Check that it is declared in a USE statement with "
                f"this name."
            )

        if len(segments) == 1:
            # Just the peripheral name — return the instance itself
            raise ConstraintEvalError(
                f"Property access '{periph_name}' is incomplete. "
                f"Specify an attribute, e.g., '{periph_name}.some_attr'."
            )

        # Remaining segments are attribute lookups
        attr_name = segments[1]

        # First check user-defined attributes (WITH clause)
        val = _get_attribute_value(periph, attr_name)
        if val is not None:
            return val

        # Then check operational attributes on the ref
        ref = periph.ref if hasattr(periph, "ref") else periph
        op = getattr(ref, "operational", None)
        if op is not None and hasattr(op, attr_name):
            raw = getattr(op, attr_name)
            # If it's a PowerConsumption, parse to mW
            if hasattr(raw, "value") and hasattr(raw, "unit"):
                parsed = _parse_power_mw(raw)
                if parsed is not None:
                    return parsed
            return raw

        # Check direct attributes on the ref
        if hasattr(ref, attr_name):
            return getattr(ref, attr_name)

        raise ConstraintEvalError(
            f"Peripheral '{periph_name}' has no attribute "
            f"'{attr_name}'. Available user attributes: "
            f"{[a.name for a in getattr(periph, 'attributes', [])]}."
        )

    raise ConstraintEvalError(f"Unknown atom expression type: {cls_name}")


def _eval_multiplicative(node, model):
    """Evaluate a MultiplicativeExpr node."""
    cls_name = type(node).__name__

    # If it's actually an atom (textX may collapse single-operand rules)
    if cls_name != "MultiplicativeExpr":
        return _eval_atom(node, model)

    operands = node.operands
    operators = node.operators

    if not operands:
        raise ConstraintEvalError("Empty multiplicative expression")

    result = _eval_atom(operands[0], model)

    for i, op in enumerate(operators):
        right = _eval_atom(operands[i + 1], model)
        if op == "*":
            result = float(result) * float(right)
        elif op == "/":
            if float(right) == 0:
                raise ConstraintEvalError("Division by zero in constraint")
            result = float(result) / float(right)

    return result


def _eval_additive(node, model):
    """Evaluate an AdditiveExpr node."""
    cls_name = type(node).__name__

    # If textX collapsed the rule
    if cls_name != "AdditiveExpr":
        return _eval_multiplicative(node, model)

    operands = node.operands
    operators = node.operators

    if not operands:
        raise ConstraintEvalError("Empty additive expression")

    result = _eval_multiplicative(operands[0], model)

    for i, op in enumerate(operators):
        right = _eval_multiplicative(operands[i + 1], model)
        if op == "+":
            result = float(result) + float(right)
        elif op == "-":
            result = float(result) - float(right)

    return result


def _eval_comparison(node, model):
    """Evaluate a ComparisonExpr node and return (bool, left_val, right_val)."""
    left_val = _eval_additive(node.left, model)
    right_val = _eval_additive(node.right, model)
    op = node.op

    # Coerce to float for numeric comparisons
    try:
        lf = float(left_val)
        rf = float(right_val)
    except (ValueError, TypeError):
        # Fall back to direct comparison for strings/bools
        lf = left_val
        rf = right_val

    if op == "<":
        return lf < rf, left_val, right_val
    elif op == ">":
        return lf > rf, left_val, right_val
    elif op == "<=":
        return lf <= rf, left_val, right_val
    elif op == ">=":
        return lf >= rf, left_val, right_val
    elif op == "==":
        return lf == rf, left_val, right_val
    elif op == "!=":
        return lf != rf, left_val, right_val

    raise ConstraintEvalError(f"Unknown comparison operator: {op}")


def _eval_constraint(constraint, model):
    """Evaluate a UserConstraint and return (passed, left_val, right_val, error).

    Returns:
        tuple: (passed: bool|None, left_val, right_val, error: str|None)
        If error is not None, passed is None.
    """
    try:
        passed, left_val, right_val = _eval_comparison(constraint.expr, model)
        return passed, left_val, right_val, None
    except ConstraintEvalError as e:
        return None, None, None, str(e)
    except Exception as e:
        return None, None, None, f"Unexpected error: {e}"


# ========================================================================
# Validator class
# ========================================================================


class UserConstraintValidator(BaseValidator):
    @staticmethod
    def get_name() -> str:
        return "User-Defined Constraints"

    @staticmethod
    def get_description() -> str:
        return "Evaluates user-defined CONSTRAINT expressions and reports " "violations as semantic errors"

    @staticmethod
    def validate(model, **kwargs):
        constraints = getattr(model, "constraints", [])
        if not constraints:
            return

        for constraint in constraints:
            name = constraint.name
            message = constraint.message or ""

            passed, left_val, right_val, error = _eval_constraint(constraint, model)

            if error is not None:
                # Evaluation error — report as warning (not error)
                # because the constraint itself may be malformed
                raise_validation_warning(
                    constraint,
                    f"[Constraint-Eval-Error] Constraint '{name}' could " f"not be evaluated: {error}",
                    "ConstraintEvalError",
                )
                continue

            if not passed:
                # Constraint violated — this is a semantic error
                op = constraint.expr.op
                if message:
                    detail = message
                else:
                    detail = f"Expression '{name}' failed: " f"{left_val} {op} {right_val} is false"

                raise_validation_error(
                    constraint,
                    f"[Constraint-Violated] Constraint '{name}' violated: "
                    f"{detail} "
                    f"(left={left_val}, right={right_val})",
                    "ConstraintViolation",
                )


def validate_user_constraints(model):
    """Module-level function for pipeline registration."""
    UserConstraintValidator.validate(model)


__all__ = [
    "UserConstraintValidator",
    "validate_user_constraints",
    "ConstraintEvalError",
]
