"""
Pin pool for SmartConnection resolution.

Manages board pin allocation with conflict-aware sharing rules:
- Power pins (GND/VCC): always shareable
- I2C SDA/SCL: shareable (bus architecture)
- All other pins: exclusive

This module was extracted from ``demol/lang/smart_connection.py`` as part
of the P0 refactor. The helper predicates (``is_io_pin``, ``is_power_pin``)
and protocol function sets (``I2C_FUNCTIONS``, ``SPI_FUNCTIONS``,
``UART_FUNCTIONS``) used here are imported from
``demol.lang.smart_connection`` to preserve all existing import paths.

To avoid a circular import, ``smart_connection.py`` defines its helpers
and constants BEFORE importing :class:`PinPool` back from this module.
"""

from __future__ import annotations


class PinPool:
    """Manages available board pins with conflict-aware allocation.

    Tracks which board pins are in use and enforces sharing rules:
    - Power pins (GND/VCC): always shareable
    - I2C SDA/SCL: shareable (bus architecture)
    - All other pins: exclusive
    """

    def __init__(self, board):
        self.board = board
        # Index all board pins by name
        self._all_pins = {p.name: p for p in board.pins}
        # Track usage: pin_name -> list of (peripheral_name, usage_type)
        self._usage = {}
        # Sort IO pins by physical pin number for deterministic allocation
        self._io_pins_sorted = sorted(
            [p for p in board.pins if is_io_pin(p)],
            key=lambda p: p.number,
        )
        self._power_pins_sorted = sorted(
            [p for p in board.pins if is_power_pin(p)],
            key=lambda p: p.number,
        )

    def mark_used(self, pin_name, peripheral_name, usage_type):
        """Mark a single pin as used by a peripheral."""
        if pin_name not in self._usage:
            self._usage[pin_name] = []
        self._usage[pin_name].append((peripheral_name, usage_type))

    def is_available(self, pin_name, usage_type):
        """Check if pin is available for given usage type.

        Sharing rules:
        - If pin has no usage entries → available
        - POWER usage → always available (power pins are shareable)
        - I2C-SDA, I2C-SCL → shareable (multiple devices on same bus)
        - Everything else → exclusive
        """
        if pin_name not in self._usage:
            return True

        existing_usages = self._usage[pin_name]

        # Power pins are always shareable
        if usage_type == "POWER":
            return all(u[1] == "POWER" for u in existing_usages)

        # I2C pins are shareable
        if usage_type.startswith("I2C-"):
            return all(u[1] == usage_type or u[1] == "POWER" for u in existing_usages)

        # Everything else is exclusive
        return False

    def mark_used_from_connections(self, connections):
        """Scan manual CONNECT blocks and mark their board pins as used.

        Called BEFORE enrichment, so we determine board pins from raw
        from_comp/to_comp references.
        """
        board_pin_names = set(self._all_pins.keys())

        for conn in connections:
            # Skip synthetic (SmartConnect-generated) connections
            if getattr(conn, "_is_smart_connection", False):
                continue

            # Determine which component is the board
            from_ref = None
            to_ref = None

            if hasattr(conn, "from_comp") and conn.from_comp:
                fc = conn.from_comp
                from_ref = fc.ref if hasattr(fc, "ref") else fc
            if hasattr(conn, "to_comp") and conn.to_comp:
                tc = conn.to_comp
                to_ref = tc.ref if hasattr(tc, "ref") else tc

            # The board component reference
            is_from_board = from_ref and "Board" in type(from_ref).__name__
            is_to_board = to_ref and "Board" in type(to_ref).__name__

            # If neither is board, check if to_comp is missing (defaults to board)
            if not is_from_board and not is_to_board:
                # When to_comp is omitted, from_comp is the peripheral,
                # and pin names on the RHS (toPin) could be board pins
                # We need to check both sides
                pass

            # Power connections
            if hasattr(conn, "powerConns"):
                for pc in conn.powerConns:
                    # Check both pins against board pin names
                    if pc.fromPin in board_pin_names:
                        self.mark_used(pc.fromPin, "manual", "POWER")
                    if pc.toPin in board_pin_names:
                        self.mark_used(pc.toPin, "manual", "POWER")

            # Data connections
            if hasattr(conn, "dataConns"):
                for dc in conn.dataConns:
                    conn_type = dc.type if hasattr(dc, "type") else "gpio"
                    for pm in dc.pins:
                        # Check which pin belongs to the board
                        if pm.fromPin in board_pin_names:
                            usage = self._infer_usage_type(conn_type, pm.fromPin)
                            self.mark_used(pm.fromPin, "manual", usage)
                        if hasattr(pm, "toPin") and pm.toPin in board_pin_names:
                            usage = self._infer_usage_type(conn_type, pm.toPin)
                            self.mark_used(pm.toPin, "manual", usage)

    def _infer_usage_type(self, conn_type, pin_name):
        """Infer usage type string from connection type and pin."""
        pin = self._all_pins.get(pin_name)
        if not pin or not is_io_pin(pin):
            return conn_type.upper()

        if conn_type == "i2c":
            # Determine if it's SDA or SCL from the board pin's functions
            for func in pin.funcs:
                if func.ptype == "sda":
                    return "I2C-SDA"
                if func.ptype == "scl":
                    return "I2C-SCL"
            return "I2C"
        elif conn_type == "spi":
            return "SPI"
        elif conn_type == "uart":
            return "UART"
        elif conn_type == "pwm":
            return "PWM"
        return "GPIO"

    def find_power_pin(self, voltage_type):
        """Find an available board power pin matching voltage type.

        Power pins are shareable, so we first try unused pins, then fall back
        to already-used ones (which are valid due to sharing).
        """
        voltage_type_upper = str(voltage_type).upper()

        # First pass: prefer unused power pins
        for pin in self._power_pins_sorted:
            pin_ptype = str(pin.ptype).upper()
            if pin_ptype == voltage_type_upper and pin.name not in self._usage:
                return pin

        # Second pass: accept already-used power pins (shareable)
        for pin in self._power_pins_sorted:
            pin_ptype = str(pin.ptype).upper()
            if pin_ptype == voltage_type_upper and self.is_available(pin.name, "POWER"):
                return pin

        return None

    def find_io_pin_by_function(self, func_type, bus=None):
        """Find available board IO pin with matching function.

        For I2C pins, they're shareable so even used pins qualify.
        """
        for pin in self._io_pins_sorted:
            for func in pin.funcs:
                if func.ptype == func_type:
                    # Check bus match if specified
                    if bus is not None and hasattr(func, "bus") and func.bus != bus:
                        continue

                    # Determine usage type for availability check
                    if func_type in I2C_FUNCTIONS:
                        usage = f"I2C-{func_type.upper()}"
                    elif func_type in SPI_FUNCTIONS:
                        usage = "SPI"
                    elif func_type in UART_FUNCTIONS:
                        usage = "UART"
                    else:
                        usage = "GPIO"

                    if self.is_available(pin.name, usage):
                        return pin

        return None

    def find_gpio_pin(self):
        """Find any available board pin with GPIO function."""
        for pin in self._io_pins_sorted:
            has_gpio = any(f.ptype == "gpio" for f in pin.funcs)
            if has_gpio and self.is_available(pin.name, "GPIO"):
                return pin
        return None

    def find_pwm_pin(self, channel=None):
        """Find available board pin with PWM function."""
        for pin in self._io_pins_sorted:
            for func in pin.funcs:
                if func.ptype == "pwm":
                    if channel is not None and hasattr(func, "channel") and func.channel != channel:
                        continue
                    if self.is_available(pin.name, "PWM"):
                        return pin
        return None


# Helper predicates and protocol function sets are owned by
# smart_connection.py and imported here AFTER the PinPool class is
# defined. The import order matters because of the circular dependency:
# smart_connection.py imports PinPool from this module, and we import
# the helpers and constants from smart_connection. By placing these
# imports at the bottom (after PinPool exists), the cycle resolves:
# pin_pool is mid-load → smart_connection begins loading → defines its
# helpers/constants → imports PinPool (already defined) → finishes →
# pin_pool resumes and binds the helper names below.
from .smart_connection import (  # noqa: E402,F401  (re-exported for convenience)
    I2C_FUNCTIONS,
    SPI_FUNCTIONS,
    UART_FUNCTIONS,
    is_io_pin,
    is_power_pin,
)


__all__ = ["PinPool", "is_io_pin", "is_power_pin",
           "I2C_FUNCTIONS", "SPI_FUNCTIONS", "UART_FUNCTIONS"]
