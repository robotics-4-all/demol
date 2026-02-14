import os
import warnings
from typing import Any, Dict, List

from .definitions import DIAGRAMS_DIRNAME, RIOT_SOURCE_DIRNAME


def create_output_dirs(out_dir: str):
    diagrams_dir = os.path.join(out_dir, DIAGRAMS_DIRNAME)
    if not os.path.exists(diagrams_dir):
        # If it doesn't exist, create it
        os.makedirs(diagrams_dir)
    riot_src_dir = os.path.join(out_dir, RIOT_SOURCE_DIRNAME)
    if not os.path.exists(riot_src_dir):
        # If it doesn't exist, create it
        os.makedirs(riot_src_dir)


class DeviceModelExtractor:
    """Extracts information from DeMoL device models."""

    def __init__(self, device_model):
        """Initialize extractor with device model.

        Args:
            device_model: Parsed DeMoL device model
        """
        self.device_model = device_model
        self.broker_config: Dict[str, Any] = {}
        self.peripherals: List[Dict[str, Any]] = []

    def extract(self) -> None:
        """Extract all information from the device model."""
        self._extract_broker_config()
        self._extract_peripherals()

    def _extract_broker_config(self) -> None:
        """Extract broker configuration."""
        broker = self.device_model.broker

        if type(broker).__name__ != "MQTTBroker":
            raise TypeError(
                "This transformation does not support other Broker types than MQTTBroker."
            )

        self.broker_config = {
            "host": broker.host,
            "port": broker.port,
            "ssl": getattr(broker, "ssl", False),
            "username": "",
            "password": "",
        }

        # Extract authentication
        auth_type = type(broker.auth).__name__

        if auth_type == "AuthPlain":
            self.broker_config["username"] = getattr(broker.auth, "username", "")
            self.broker_config["password"] = getattr(broker.auth, "password", "")
        elif auth_type in ("AuthCert", "AuthApiKey"):
            raise TypeError(
                "This transformation uses commlib-py library and only supports "
                "plain authentication for MQTTBroker."
            )
        else:
            # Warn about missing authentication for remote brokers
            if self.broker_config["host"] != "localhost" and not (
                self.broker_config["username"] and self.broker_config["password"]
            ):
                warnings.warn(
                    "You are using a remote broker without authentication. "
                    "This is not secure. Add username and password to your .dev file."
                )

    def _extract_peripherals(self) -> None:
        """Extract peripheral configurations."""
        for conn in self.device_model.connections:
            # Extract pins first to get bus information
            pins = self._extract_pins(conn.dataConns)

            peripheral_info = {
                "instance": conn.peripheral.name,
                "name": conn.peripheral.ref.name,
                "class": conn.peripheral.ref.type,
                "type": type(conn.peripheral.ref).__name__,
                "peripheral_ref": conn.peripheral.ref,  # Pass the full peripheral reference
                "board_ref": self.device_model.components.board,  # Pass the board reference
                "pins": pins,
                "attributes": self._extract_attributes(conn.peripheral.ref.attributes),
                "topic": conn.remote,
            }

            # Add bus information to top level for easy access in templates
            if "i2c_bus" in pins:
                peripheral_info["i2c_bus"] = pins["i2c_bus"]
            if "spi_bus" in pins:
                peripheral_info["spi_bus"] = pins["spi_bus"]
            if "uart_port" in pins:
                peripheral_info["uart_port"] = pins["uart_port"]

            self.peripherals.append(peripheral_info)

    def _extract_pins(self, data_conns) -> Dict[str, Any]:
        """Extract pin mappings from data connections."""
        pins = {}

        # Get board reference to access pin definitions
        board = self.device_model.components.board
        board_pins_map = {pin.name: pin for pin in board.pins}

        for data_conn in data_conns:
            conn_type = data_conn.type

            if conn_type == "gpio":
                # Extract GPIO properties
                gpio_props = {}
                for prop in data_conn.props:
                    if prop.name in ["mode", "pullup", "pulldown"]:
                        gpio_props[prop.name] = prop.value

                # Handle pins based on peripheral pin name
                for pin_map in data_conn.pins:
                    key = pin_map.peripheralPin
                    pins[key] = pin_map.boardPin
                    pins[f"{key}_props"] = gpio_props

            elif conn_type == "spi":
                # Extract SPI properties
                spi_props = {}
                for prop in data_conn.props:
                    if prop.name in ["bus_speed", "mode"]:
                        spi_props[prop.name] = prop.value

                for pin_map in data_conn.pins:
                    board_pin = board_pins_map.get(pin_map.boardPin)

                    if pin_map.function == "mosi":
                        pins["mosi"] = pin_map.boardPin
                        # Extract SPI bus from board pin's function definition
                        if board_pin:
                            pins["spi_bus"] = self._get_bus_from_pin(board_pin, "mosi")
                    elif pin_map.function == "miso":
                        pins["miso"] = pin_map.boardPin
                    elif pin_map.function == "sck":
                        pins["sck"] = pin_map.boardPin
                    elif pin_map.function == "cs":
                        pins["cs"] = pin_map.boardPin
                    pins[f"{pin_map.function}_props"] = spi_props

            elif conn_type == "i2c":
                # Extract I2C properties
                i2c_props = {}
                for prop in data_conn.props:
                    if prop.name in ["slave_address", "bus_speed"]:
                        i2c_props[prop.name] = prop.value

                for pin_map in data_conn.pins:
                    board_pin = board_pins_map.get(pin_map.boardPin)

                    if pin_map.function == "sda":
                        pins["sda"] = pin_map.boardPin
                        # Extract I2C bus from board pin's function definition
                        if board_pin:
                            pins["i2c_bus"] = self._get_bus_from_pin(board_pin, "sda")
                    elif pin_map.function == "scl":
                        pins["scl"] = pin_map.boardPin
                    pins[f"{pin_map.function}_props"] = i2c_props

            elif conn_type == "uart":
                # Extract UART properties
                uart_props = {}
                for prop in data_conn.props:
                    if prop.name in ["baudrate", "parity", "stop_bits", "data_bits"]:
                        uart_props[prop.name] = prop.value

                for pin_map in data_conn.pins:
                    board_pin = board_pins_map.get(pin_map.boardPin)

                    if pin_map.function == "tx":
                        pins["tx"] = pin_map.boardPin
                        # Extract UART port from board pin's function definition
                        if board_pin:
                            pins["uart_port"] = self._get_bus_from_pin(board_pin, "tx")
                    elif pin_map.function == "rx":
                        pins["rx"] = pin_map.boardPin
                    pins[f"{pin_map.function}_props"] = uart_props

            else:
                raise TypeError(f"Not a valid IO Connection Type: {conn_type}")

        return pins

    def _get_bus_from_pin(self, board_pin, function_type: str) -> int:
        """Extract bus number from board pin's function definition.

        Args:
            board_pin: Board pin object with funcs attribute
            function_type: Type of function to look for (e.g., 'sda', 'mosi', 'tx')

        Returns:
            Bus number as integer, defaults to 0 if not found
        """
        if hasattr(board_pin, "funcs"):
            for func in board_pin.funcs:
                # Check if this function matches the type we're looking for
                if hasattr(func, "ptype") and func.ptype == function_type:
                    # Return the bus number from the function definition
                    if hasattr(func, "bus"):
                        return int(func.bus)
        return 0

    def _extract_attributes(self, attributes) -> Dict[str, Any]:
        """Extract attributes from peripheral."""
        result = {}

        for attr in attributes:
            attr_type = type(attr).__name__

            if attr_type == "DictAttribute":
                result[attr.name] = self._convert_dict_attribute(attr)
            else:
                result[attr.name] = attr.default

        return result

    def _convert_dict_attribute(self, attribute) -> Dict[str, Any]:
        """Recursively convert DictAttribute to dict."""
        result = {}

        for item in attribute.items:
            item_type = type(item).__name__

            if item_type in ("DictAttribute", "DictSetting"):
                result[item.name] = self._convert_dict_attribute(item)
            else:
                result[item.name] = item.default

        return result
