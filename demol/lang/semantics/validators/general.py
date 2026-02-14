"""General and cross-cutting validators.

This module contains validators that don't fit into specific categories:
- Dependency sources validation
- Connections orchestration (validates all connection types)
"""

from ..core import raise_validation_error
from ..utils import get_connection_endpoints
from .base import BaseValidator


class DependencySourcesValidator(BaseValidator):
    """Validates dependency source values."""

    @staticmethod
    def get_name() -> str:
        return "Dependency Sources Validation"

    @staticmethod
    def get_description() -> str:
        return "Ensures dependency source values are valid (pip or apt)"

    @staticmethod
    def validate(component):
        """
        Validate that dependency source values are valid.

        Ensures that the 'source' field in dependencies only contains
        valid values: "pip" or "apt".
        """
        if not hasattr(component, "dependencies") or not component.dependencies:
            return

        valid_sources = {"pip", "apt"}

        for dep_mapping in component.dependencies:
            if not hasattr(dep_mapping, "items") or not dep_mapping.items:
                continue

            for item in dep_mapping.items:
                # Skip string-only dependencies (they don't have a source field)
                if isinstance(item, str):
                    continue

                # Check if the item has a source field
                if hasattr(item, "source") and item.source:
                    source_value = item.source.strip('"').strip("'")

                    if source_value not in valid_sources:
                        raise_validation_error(
                            component,
                            f"Invalid dependency source '{source_value}' for package '{item.name}'. "
                            f"Valid sources are: {', '.join(sorted(valid_sources))}",
                            "InvalidDependencySourceError",
                        )


class ConnectionsOrchestratorValidator(BaseValidator):
    """Orchestrates validation of all connection types."""

    @staticmethod
    def get_name() -> str:
        return "Connections Validation"

    @staticmethod
    def get_description() -> str:
        return "Validates all connections (power and data) in the model"

    @staticmethod
    def validate(model):
        """
        Validate all connections in the model.

        Iterates over all connections and performs specific validations for
        power and data connections.
        """
        # Import validators here to avoid circular imports
        from .power import validate_power_connection
        from .communication import (
            validate_gpio_connection,
            validate_i2c_connection,
            validate_spi_connection,
            validate_uart_connection,
            validate_pwm_connection,
        )

        board = model.components.board

        # Also collect power sources for pin lookup

        for c in model.connections:
            from_ref, from_name, to_ref, to_name = get_connection_endpoints(c)

            if from_ref is None or to_ref is None:
                continue

            # Determine which component is the board and which is the peripheral/power source
            # This is needed because pin connections are always written from the power source
            # perspective (board_pin -- peripheral_pin), regardless of CONNECT statement order
            is_from_board = from_ref == board
            is_to_board = to_ref == board

            # Build pin maps for both components
            from_pins_map = {p.name: p for p in from_ref.pins}
            to_pins_map = {p.name: p for p in to_ref.pins}
            from_pin_names = set(from_pins_map.keys())
            to_pin_names = set(to_pins_map.keys())

            # ====================================================================
            # Validate Power Connections
            # ====================================================================
            for pconn in c.powerConns:
                # Horizontal pin logic: fromPin is on from_comp, toPin is on to_comp
                # This is consistent for both power and data connections

                # Check if fromPin exists on from_comp
                if pconn.fromPin not in from_pin_names:
                    raise_validation_error(
                        pconn, f"Pin '{pconn.fromPin}' not found on '{from_name}'."
                    )
                    continue

                # Check if toPin exists on to_comp
                if pconn.toPin not in to_pin_names:
                    raise_validation_error(
                        pconn, f"Pin '{pconn.toPin}' not found on '{to_name}'."
                    )
                    continue

                from_pin_obj = from_pins_map[pconn.fromPin]
                to_pin_obj = to_pins_map[pconn.toPin]

                # Validate power connection (check voltage compatibility)
                if hasattr(from_pin_obj, "ptype") and hasattr(to_pin_obj, "ptype"):
                    if is_from_board:
                        validate_power_connection(from_pin_obj, to_pin_obj, pconn)
                    elif is_to_board:
                        validate_power_connection(to_pin_obj, from_pin_obj, pconn)

            # ====================================================================
            # Validate IO Connections
            # ====================================================================
            for data_conn in c.dataConns:
                conn_type = data_conn.type

                # Helper to get property value
                def get_prop(name, default=None):
                    for p in data_conn.props:
                        if p.name == name:
                            val = p.value
                            if isinstance(val, str) and val.lower().startswith("0x"):
                                try:
                                    return int(val, 16)
                                except ValueError:
                                    return val
                            return val
                    return default

                # Helper to get pin mapping
                def get_pin(func_name):
                    for p in data_conn.pins:
                        if p.function == func_name:
                            return p
                    return None

                # Determine pin ownership for data connections (horizontal logic)
                # fromPin is on from_comp, toPin is on to_comp
                data_source_pins_map = from_pins_map
                data_source_pin_names = from_pin_names
                data_source_name = from_name
                data_sink_pins_map = to_pins_map
                data_sink_pin_names = to_pin_names
                data_sink_name = to_name

                # Collect all used pins for this data connection
                pins_valid = True
                for pin_map in data_conn.pins:
                    # Check if fromPin exists on source component
                    if pin_map.fromPin not in data_source_pin_names:
                        raise_validation_error(
                            pin_map,
                            f"Source pin '{pin_map.fromPin}' not found on '{data_source_name}'.",
                        )
                        pins_valid = False
                    # Check if toPin exists on sink component
                    if pin_map.toPin not in data_sink_pin_names:
                        raise_validation_error(
                            pin_map,
                            f"Target pin '{pin_map.toPin}' not found on '{data_sink_name}'.",
                        )
                        pins_valid = False

                if not pins_valid:
                    continue

                if conn_type == "gpio":
                    pin_conn = data_conn.pins[0]  # Assuming single pin for GPIO for now

                    # Enhanced validation: Check GPIO functionality
                    source_pin = data_source_pins_map[pin_conn.fromPin]
                    sink_pin = data_sink_pins_map[pin_conn.toPin]
                    validate_gpio_connection(source_pin, sink_pin, data_conn)

                elif conn_type == "i2c":
                    sda = get_pin("sda")
                    scl = get_pin("scl")
                    slave_addr = get_prop("slave_address")

                    if not sda or not scl:
                        # TODO: Better error handling for missing pins
                        continue

                    # Enhanced validation: Check I2C functionality and address range
                    source_sda = data_source_pins_map[sda.fromPin]
                    source_scl = data_source_pins_map[scl.fromPin]
                    sink_sda = data_sink_pins_map[sda.toPin]
                    sink_scl = data_sink_pins_map[scl.toPin]
                    validate_i2c_connection(
                        source_sda,
                        source_scl,
                        sink_sda,
                        sink_scl,
                        slave_addr,
                        data_conn,
                    )

                elif conn_type == "spi":
                    miso = get_pin("miso")
                    mosi = get_pin("mosi")
                    sck = get_pin("sck")
                    cs = get_pin("cs")

                    # Enhanced validation: Check SPI functionality
                    source_spi_pins = {
                        "mosi": data_source_pins_map[mosi.fromPin] if mosi else None,
                        "miso": data_source_pins_map[miso.fromPin] if miso else None,
                        "sck": data_source_pins_map[sck.fromPin] if sck else None,
                        "cs": data_source_pins_map[cs.fromPin] if cs else None,
                    }
                    sink_spi_pins = {
                        "mosi": data_sink_pins_map[mosi.toPin] if mosi else None,
                        "miso": data_sink_pins_map[miso.toPin] if miso else None,
                        "sck": data_sink_pins_map[sck.toPin] if sck else None,
                        "cs": data_sink_pins_map[cs.toPin] if cs else None,
                    }
                    validate_spi_connection(source_spi_pins, sink_spi_pins, data_conn)

                elif conn_type == "uart":
                    tx = get_pin("tx")
                    rx = get_pin("rx")
                    baudrate = get_prop("baudrate")

                    if not tx or not rx:
                        continue

                    # Enhanced validation: Check UART functionality
                    # We need to pass (board_tx, board_rx, periph_tx, periph_rx)
                    # Check which side is board

                    # Get pins from mappings
                    # tx mapping: function="tx", fromPin=source_pin, toPin=sink_pin
                    # rx mapping: function="rx", fromPin=source_pin, toPin=sink_pin

                    # Note: "tx" mapping usually connects Board TX to Peripheral RX
                    # or Peripheral TX to Board RX?
                    # Actually, the mapping defines which pins are used for the "tx" line and "rx" line.
                    # But typically we map TX-RX and RX-TX.
                    # Let's assume the pins are just the endpoints of the connection.

                    pin_tx_source = data_source_pins_map[tx.fromPin] if tx else None
                    pin_tx_sink = data_sink_pins_map[tx.toPin] if tx else None
                    pin_rx_source = data_source_pins_map[rx.fromPin] if rx else None
                    pin_rx_sink = data_sink_pins_map[rx.toPin] if rx else None

                    if is_from_board:
                        # Source is Board, Sink is Peripheral
                        validate_uart_connection(
                            pin_tx_source,
                            pin_rx_source,
                            pin_tx_sink,
                            pin_rx_sink,
                            baudrate,
                            data_conn,
                        )
                    elif is_to_board:
                        # Source is Peripheral, Sink is Board
                        validate_uart_connection(
                            pin_tx_sink,
                            pin_rx_sink,
                            pin_tx_source,
                            pin_rx_source,
                            baudrate,
                            data_conn,
                        )
                    else:
                        # Peripheral to Peripheral? Not supported by validate_uart_connection yet
                        # Or treat source as board?
                        pass

                elif conn_type == "pwm":
                    pin_conn = data_conn.pins[0]  # Assuming single pin for PWM for now

                    # Enhanced validation: Check PWM functionality
                    source_pin = data_source_pins_map[pin_conn.fromPin]
                    sink_pin = data_sink_pins_map[pin_conn.toPin]

                    # Determine which pin is the board pin
                    if is_from_board:
                        validate_pwm_connection(source_pin, sink_pin, data_conn)
                    elif is_to_board:
                        validate_pwm_connection(sink_pin, source_pin, data_conn)
                    else:
                        # Peripheral to Peripheral - treat source as board
                        validate_pwm_connection(source_pin, sink_pin, data_conn)


# Convenience function exports (for backward compatibility)
def validate_dependency_sources(component):
    """Validate dependency sources."""
    DependencySourcesValidator.validate(component)


def validate_connections(model):
    """Validate all connections."""
    ConnectionsOrchestratorValidator.validate(model)


__all__ = [
    "DependencySourcesValidator",
    "ConnectionsOrchestratorValidator",
    "validate_dependency_sources",
    "validate_connections",
]
