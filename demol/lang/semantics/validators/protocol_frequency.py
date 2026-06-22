"""Protocol frequency/bus speed validators.

This module validates bus speed settings on I2C and SPI connections:
- [Safety-I2C-BusSpeed] I2C bus_speed must be a standard mode
- [Safety-SPI-BusSpeed] SPI bus_speed must be within reasonable limits
- [Warning-I2C-HighSpeed] Warn when using fast-mode-plus or high-speed I2C
"""

import logging
from ..core import raise_validation_error, raise_validation_warning
from .base import BaseValidator

logger = logging.getLogger(__name__)

# Standard I2C modes (name, max_freq_hz)
I2C_MODES = [
    ("Standard Mode", 100_000),
    ("Fast Mode", 400_000),
    ("Fast Mode Plus", 1_000_000),
    ("High Speed Mode", 3_400_000),
]

# Maximum reasonable SPI clock (most MCUs cap at 80 MHz)
SPI_MAX_REASONABLE_HZ = 80_000_000


def _classify_i2c_speed(speed_hz):
    """Return the I2C mode name for a given bus speed."""
    for name, max_freq in I2C_MODES:
        if speed_hz <= max_freq:
            return name, max_freq
    return "Beyond High Speed", I2C_MODES[-1][1]


class ProtocolFrequencyValidator(BaseValidator):
    """Validates bus speed settings on I2C and SPI connections."""

    @staticmethod
    def get_name() -> str:
        return "Protocol Frequency Validation"

    @staticmethod
    def get_description() -> str:
        return "Validates I2C/SPI bus_speed against standard modes and device capabilities"

    @staticmethod
    def validate(model, **kwargs):
        """
        Validate bus speed properties on all data connections.

        Rules:
        - [Safety-I2C-BusSpeed] I2C bus_speed must be a recognized standard
          mode (100k, 400k, 1M, 3.4M). Values above 3.4 MHz are errors.
        - [Warning-I2C-HighSpeed] Warn when using Fast Mode Plus (1 MHz) or
          High Speed Mode (3.4 MHz) — many peripherals only support up to
          400 kHz (Fast Mode).
        - [Safety-SPI-BusSpeed] SPI bus_speed must be positive and below
          80 MHz (reasonable MCU limit).
        """
        connections = getattr(model, "connections", [])
        if not connections:
            return

        for conn in connections:
            data_conns = getattr(conn, "dataConns", [])
            if not data_conns:
                continue

            # Resolve peripheral name for error messages
            periph_name = "unknown"
            from_comp = getattr(conn, "from_comp", None)
            if from_comp:
                periph_name = getattr(from_comp, "name", "unknown")

            for dconn in data_conns:
                conn_type = getattr(dconn, "type", "")
                props = getattr(dconn, "props", [])

                for prop in props:
                    if prop.name != "bus_speed":
                        continue

                    speed = prop.value
                    # Handle string hex values
                    if isinstance(speed, str):
                        try:
                            speed = int(speed, 0)
                        except (ValueError, TypeError):
                            raise_validation_error(
                                dconn,
                                f"[Safety-BusSpeed] Invalid bus_speed "
                                f"value '{prop.value}' on {conn_type.upper()} "
                                f"connection for '{periph_name}'. "
                                f"Must be a positive integer (Hz).",
                                "BusSpeedValueError",
                            )
                            continue

                    if not isinstance(speed, (int, float)) or speed <= 0:
                        raise_validation_error(
                            dconn,
                            f"[Safety-BusSpeed] bus_speed must be a "
                            f"positive number on {conn_type.upper()} "
                            f"connection for '{periph_name}', "
                            f"got {speed}.",
                            "BusSpeedValueError",
                        )
                        continue

                    speed = int(speed)

                    if conn_type == "i2c":
                        _validate_i2c_bus_speed(dconn, speed, periph_name)
                    elif conn_type == "spi":
                        _validate_spi_bus_speed(dconn, speed, periph_name)


def _validate_i2c_bus_speed(dconn, speed_hz, periph_name):
    """Validate I2C bus speed against standard modes."""
    mode_name, mode_max = _classify_i2c_speed(speed_hz)

    # Beyond High Speed Mode (3.4 MHz) — error
    if speed_hz > I2C_MODES[-1][1]:
        raise_validation_error(
            dconn,
            f"[Safety-I2C-BusSpeed] I2C bus_speed {speed_hz:,} Hz "
            f"for '{periph_name}' exceeds the maximum I2C High Speed "
            f"Mode ({I2C_MODES[-1][1]:,} Hz). "
            f"Valid I2C modes: Standard (100 kHz), Fast (400 kHz), "
            f"Fast Mode Plus (1 MHz), High Speed (3.4 MHz).",
            "I2CBusSpeedError",
        )
        return

    # Fast Mode Plus or High Speed — warning (many devices only support
    # up to 400 kHz Fast Mode)
    if speed_hz > 400_000:
        raise_validation_warning(
            dconn,
            f"[Warning-I2C-HighSpeed] I2C bus_speed {speed_hz:,} Hz "
            f"for '{periph_name}' uses {mode_name} "
            f"(max {mode_max:,} Hz). Many I2C peripherals only "
            f"support up to 400 kHz (Fast Mode). Verify that "
            f"'{periph_name}' supports this speed.",
            "I2CHighSpeedWarning",
        )


def _validate_spi_bus_speed(dconn, speed_hz, periph_name):
    """Validate SPI bus speed against reasonable limits."""
    if speed_hz > SPI_MAX_REASONABLE_HZ:
        raise_validation_error(
            dconn,
            f"[Safety-SPI-BusSpeed] SPI bus_speed {speed_hz:,} Hz "
            f"for '{periph_name}' exceeds the reasonable maximum "
            f"of {SPI_MAX_REASONABLE_HZ:,} Hz (80 MHz). "
            f"Most MCUs and peripherals do not support SPI clocks "
            f"above this limit.",
            "SPIBusSpeedError",
        )


def validate_protocol_frequency(model, **kwargs):
    """Convenience function for backward compatibility."""
    ProtocolFrequencyValidator.validate(model, **kwargs)


__all__ = [
    "ProtocolFrequencyValidator",
    "validate_protocol_frequency",
]
