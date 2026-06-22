"""Peripheral-specific validators.

This module contains validators for peripheral-related semantic rules:
- Peripheral connectivity (all peripherals must be connected)
- Essential pins connected
- Unique peripheral names
"""

from ..core import raise_validation_error, raise_validation_warning
from ..utils import get_connection_target, get_connection_endpoints
from .base import BaseValidator


class PeripheralConnectivityValidator(BaseValidator):
    """Validates that all peripherals are connected."""

    @staticmethod
    def get_name() -> str:
        return "Peripheral Connectivity"

    @staticmethod
    def get_description() -> str:
        return "Ensures all peripherals have at least one connection defined"

    @staticmethod
    def validate(model):
        """
        Validate WF-All-Peripherals-Connected.

        From SEMANTICS.md Section 8.4:
            ∀p ∈ components.peripherals. ∃k ∈ connections. k.peripheral = p
        """
        connected_targets = {get_connection_target(conn)[1] for conn in model.connections}
        all_peripherals = {p.name for p in model.components.peripherals}
        all_power_sources = {ps.name for ps in model.components.powerSources}

        unconnected_periphs = all_peripherals - connected_targets
        unconnected_sources = all_power_sources - connected_targets

        if unconnected_periphs:
            raise_validation_error(
                model,
                f"[WF-All-Peripherals-Connected] Unconnected peripherals detected: {', '.join(unconnected_periphs)}. "
                f"All peripherals must have at least one connection defined.",
                "UnconnectedPeripheralError",
            )

        if unconnected_sources:
            raise_validation_warning(
                model,
                f"[WF-Power-Sources-Connected] Unconnected power sources detected: {', '.join(unconnected_sources)}. "
                f"Power sources should be connected to the board or a peripheral.",
                "UnconnectedPowerSourceWarning",
            )


class EssentialPinsValidator(BaseValidator):
    """Validates that essential pins are connected."""

    @staticmethod
    def get_name() -> str:
        return "Essential Pins Connected"

    @staticmethod
    def get_description() -> str:
        return "Ensures all pins marked as 'essential' are actually connected"

    @staticmethod
    def validate(model):
        """
        Validate that all pins marked as 'essential' in the peripheral definition
        are actually connected in the device model.
        """

        for periph_def in model.components.peripherals:
            peripheral_ref = periph_def.ref
            # A pin is essential if 'optional' is NOT '?'
            essential_pins = [p for p in peripheral_ref.pins if getattr(p, "optional", None) != "?"]

            if not essential_pins:
                continue

            # Find all connections for this peripheral instance
            # Check both as target and as source
            connected_pin_names = set()
            for conn in model.connections:
                from_ref, from_name, to_ref, to_name = get_connection_endpoints(conn)

                # Determine if this peripheral is involved in this connection
                is_from_periph = from_name == periph_def.name
                is_to_periph = to_name == periph_def.name

                if not (is_from_periph or is_to_periph):
                    continue

                # Collect connected pins from power connections
                # Power connections follow: fromPin is on from_comp, toPin is on to_comp
                for pconn in conn.powerConns:
                    if is_from_periph:
                        # Peripheral is from_comp, so fromPin is peripheral pin
                        connected_pin_names.add(pconn.fromPin)
                    if is_to_periph:
                        # Peripheral is to_comp, so toPin is peripheral pin
                        connected_pin_names.add(pconn.toPin)

                # Collect connected pins from data connections
                # Horizontal logic: fromPin is on from_comp, toPin is on to_comp
                for dconn in conn.dataConns:
                    for pin_map in dconn.pins:
                        if is_from_periph:
                            connected_pin_names.add(pin_map.fromPin)
                        if is_to_periph:
                            connected_pin_names.add(pin_map.toPin)

            for pin in essential_pins:
                if pin.name not in connected_pin_names:
                    raise_validation_error(
                        periph_def,
                        f"[WF-Essential-Pins] Essential pin '{pin.name}' of peripheral '{periph_def.name}' "
                        f"(type: {peripheral_ref.name}) is not connected.",
                        "MissingEssentialConnectionError",
                    )


class UniquePeripheralNamesValidator(BaseValidator):
    """Validates that peripheral names are unique."""

    @staticmethod
    def get_name() -> str:
        return "Unique Peripheral Names"

    @staticmethod
    def get_description() -> str:
        return "Ensures all peripheral instances have unique identifiers"

    @staticmethod
    def validate(model):
        """
        Validate that all peripherals have unique names.

        From SEMANTICS.md Section 4.1 (implied well-formedness):
            All peripheral instances must have unique identifiers.
        """
        peripheral_names = set()

        for peripheral_def in model.components.peripherals:
            name = peripheral_def.name
            if name in peripheral_names:
                raise_validation_error(
                    peripheral_def,
                    f"[WF-Unique-Peripheral-Names] Duplicate peripheral name '{name}'. "
                    f"Peripheral names must be unique within the device.",
                    "DuplicatePeripheralNameError",
                )
            peripheral_names.add(name)


# Convenience function exports (for backward compatibility)
def validate_all_peripherals_connected(model):
    """Validate that all peripherals are connected."""
    PeripheralConnectivityValidator.validate(model)


def validate_essential_pins_connected(model):
    """Validate that essential pins are connected."""
    EssentialPinsValidator.validate(model)


def validate_unique_peripheral_names(model):
    """Validate that peripheral names are unique."""
    UniquePeripheralNamesValidator.validate(model)


__all__ = [
    "PeripheralConnectivityValidator",
    "EssentialPinsValidator",
    "UniquePeripheralNamesValidator",
    "validate_all_peripherals_connected",
    "validate_essential_pins_connected",
    "validate_unique_peripheral_names",
]
