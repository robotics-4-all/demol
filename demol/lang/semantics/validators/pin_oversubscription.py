"""Pin function oversubscription warnings.

Rule [Warning-Pin-Oversubscription]: When a multi-function board pin is used
in a lower-priority mode (e.g., GPIO) while it also supports a higher-priority
bus (e.g., I2C SDA), warn the user that the bus becomes unavailable.
"""

from typing import Dict, List, Tuple
from ..core import raise_validation_warning
from ..utils import get_connection_endpoints
from .base import BaseValidator

PROTOCOL_PRIORITY = {
    "gpio": 0,
    "adc": 0,
    "dac": 0,
    "pwm": 1,
    "tx": 2,
    "rx": 2,
    "mosi": 3,
    "miso": 3,
    "sck": 3,
    "cs": 3,
    "sda": 4,
    "scl": 4,
}

BUS_FUNCTION_LABELS = {
    "sda": "I2C",
    "scl": "I2C",
    "mosi": "SPI",
    "miso": "SPI",
    "sck": "SPI",
    "cs": "SPI",
    "tx": "UART",
    "rx": "UART",
}


def _get_all_pin_functions(pin) -> List[Tuple[str, int]]:
    if not hasattr(pin, "funcs"):
        return []

    result = []
    for func in pin.funcs:
        ptype = getattr(func, "ptype", None)
        if ptype:
            bus = getattr(func, "bus", None)
            bus_num = int(bus) if bus is not None else -1
            result.append((str(ptype), bus_num))
    return result


def _higher_priority_functions(pin_funcs, used_as):
    higher = []
    used_priority = PROTOCOL_PRIORITY.get(used_as, 0)

    for func_type, bus_num in pin_funcs:
        func_priority = PROTOCOL_PRIORITY.get(func_type, 0)
        if func_priority > used_priority:
            label = BUS_FUNCTION_LABELS.get(func_type, func_type.upper())
            bus_suffix = f" bus {bus_num}" if bus_num >= 0 else ""
            higher.append(f"{label}{bus_suffix} ({func_type.upper()})")

    return higher


class PinOversubscriptionValidator(BaseValidator):
    @staticmethod
    def get_name() -> str:
        return "Pin Function Oversubscription"

    @staticmethod
    def get_description() -> str:
        return (
            "Warns when multi-function pins are used in low-priority modes, " "disabling higher-priority bus functions"
        )

    @staticmethod
    def validate(model, **kwargs):
        board = getattr(model.components, "board", None)
        if board is None:
            return

        board_pins_map: Dict[str, object] = {p.name: p for p in board.pins}

        for connection in model.connections:
            from_ref, from_name, to_ref, to_name = get_connection_endpoints(connection)
            if from_ref is None or to_ref is None:
                continue

            is_from_board = from_ref == board
            target_name = to_name if is_from_board else from_name

            if not hasattr(connection, "dataConns"):
                continue

            for data_conn in connection.dataConns:
                conn_type = getattr(data_conn, "type", "gpio")

                for pin_map in data_conn.pins:
                    board_pin_name = pin_map.fromPin if is_from_board else getattr(pin_map, "toPin", pin_map.fromPin)

                    board_pin = board_pins_map.get(board_pin_name)
                    if board_pin is None:
                        continue

                    pin_funcs = _get_all_pin_functions(board_pin)
                    if len(pin_funcs) <= 1:
                        continue

                    if conn_type in ("gpio", "pwm"):
                        used_as = conn_type
                    elif conn_type in ("i2c", "spi", "uart"):
                        used_as = getattr(pin_map, "function", conn_type)
                    else:
                        used_as = conn_type

                    lost = _higher_priority_functions(pin_funcs, used_as)
                    if lost:
                        raise_validation_warning(
                            connection,
                            f"[Warning-Pin-Oversubscription] Board pin "
                            f"'{board_pin_name}' used as {conn_type.upper()} "
                            f"by '{target_name}' — this disables: "
                            f"{', '.join(lost)}. "
                            f"Use a different pin if you need those buses.",
                            "PinOversubscriptionWarning",
                        )


def validate_pin_oversubscription(model):
    PinOversubscriptionValidator.validate(model)


__all__ = [
    "PinOversubscriptionValidator",
    "validate_pin_oversubscription",
]
