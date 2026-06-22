"""SmartConnect-specific validators.

Pin-level validation (conflicts, voltage, I2C address) is handled by existing
validators since SmartConnect produces standard connection objects.
"""

from ..core import raise_validation_error
from ..utils import get_connection_target
from .base import BaseValidator


class SmartConnectValidator(BaseValidator):
    """Validates SmartConnect structural constraints."""

    @staticmethod
    def get_name() -> str:
        return "SmartConnect Validation"

    @staticmethod
    def get_description() -> str:
        return "Validates SmartConnect structural constraints"

    @staticmethod
    def validate(model, **kwargs):
        if not hasattr(model, "smartConnections") or not model.smartConnections:
            return

        # Collect manual CONNECT targets
        manual_targets = set()
        for conn in model.connections:
            if not getattr(conn, "_is_smart_connection", False):
                _, target_name = get_connection_target(conn)
                if target_name != "unknown":
                    manual_targets.add(target_name)

        sc_targets = set()
        for sc in model.smartConnections:
            target_name = sc.target.name
            target_class = type(sc.target.ref).__name__

            # Rule 1: Not a board
            if "Board" in target_class:
                raise_validation_error(
                    sc,
                    "SMARTCONNECT cannot target board " f"'{target_name}'. Only sensors and actuators are supported.",
                    "SmartConnect-Target",
                )
                continue

            # Rule 2: No duplicate SmartConnect
            if target_name in sc_targets:
                raise_validation_error(
                    sc,
                    f"Duplicate SMARTCONNECT for "
                    f"'{target_name}'. Each peripheral can have at most one SMARTCONNECT.",
                    "SmartConnect-Duplicate",
                )

            # Rule 3: No conflict with manual CONNECT
            if target_name in manual_targets:
                raise_validation_error(
                    sc,
                    f"Peripheral '{target_name}' already has "
                    f"a manual CONNECT block. Use either CONNECT or SMARTCONNECT, not both.",
                    "SmartConnect-Conflict",
                )

            sc_targets.add(target_name)


def validate_smart_connections(model):
    SmartConnectValidator.validate(model)


__all__ = [
    "SmartConnectValidator",
    "validate_smart_connections",
]
