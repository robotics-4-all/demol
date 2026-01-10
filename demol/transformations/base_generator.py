"""Abstract base class for code generators with model access.

This module provides a base class that all platform-specific code generators
(RPI, ESP, etc.) can inherit from to reuse common model querying functionality.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List
import warnings
import logging

import jinja2

logger = logging.getLogger(__name__)


class BaseCodeGenerator(ABC):
    """Abstract base class for code generators with direct model access.
    
    This class provides common functionality for querying textX device models
    and extracting information needed for code generation. Platform-specific
    generators should inherit from this class and implement the abstract methods.
    """
    
    def __init__(self, device_model, output_dir: Path):
        """Initialize generator with device model and output directory.
        
        Args:
            device_model: Parsed textX device model
            output_dir: Directory where generated code will be written
        """
        self.device_model = device_model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    # ===== Common Model Query Methods =====
    
    def get_broker_config(self) -> Dict[str, Any]:
        """Query broker configuration from device model.
        
        Returns:
            Dictionary containing broker configuration (host, port, ssl, auth)
            
        Raises:
            TypeError: If broker is not an MQTTBroker
        """
        broker = self.device_model.broker
        
        if type(broker).__name__ != "MQTTBroker":
            raise TypeError(
                "This transformation does not support other Broker types than MQTTBroker."
            )
        
        config = {
            "host": broker.host,
            "port": broker.port,
            "ssl": getattr(broker, "ssl", False),
            "username": "",
            "password": "",
        }
        
        # Extract authentication
        auth_type = type(broker.auth).__name__
        
        if auth_type == "AuthPlain":
            config["username"] = getattr(broker.auth, "username", "")
            config["password"] = getattr(broker.auth, "password", "")
        elif auth_type in ("AuthCert", "AuthApiKey"):
            raise TypeError(
                "This transformation uses commlib-py library and only supports "
                "plain authentication for MQTTBroker."
            )
        
        return config
    
    def get_board(self):
        """Query board from device model.
        
        Returns:
            Board object from the model
        """
        return self.device_model.components.board
    
    def get_connections(self) -> List:
        """Query all peripheral connections from device model.
        
        Returns:
            List of connection objects
        """
        return self.device_model.connections
    
    def get_peripheral_attributes(self, peripheral_ref) -> Dict[str, Any]:
        """Extract attributes from peripheral definition.
        
        Args:
            peripheral_ref: Reference to peripheral object with attributes
            
        Returns:
            Dictionary of attribute name-value pairs
        """
        result = {}
        for item in peripheral_ref.attributes:
            result[item.name] = self._convert_attribute_value(item.default)
        return result

    def get_platform_attributes(self, obj, os_name: str) -> Dict[str, Any]:
        """Extract platform-specific attributes for a given OS.
        
        Args:
            obj: Object with platforms attribute (e.g., Board)
            os_name: Name of the operating system (e.g., 'riotos', 'raspbian')
            
        Returns:
            Dictionary of attribute name-value pairs
        """
        result = {}
        if hasattr(obj, 'platforms') and obj.platforms:
            for platform in obj.platforms:
                if platform.os == os_name:
                    for attr in platform.attributes:
                        result[attr.name] = self._convert_attribute_value(attr.value)
                    break
        return result

    def get_operational_attributes(self, peripheral_ref) -> Dict[str, Any]:
        """Extract operational attributes from peripheral definition.
        
        Args:
            peripheral_ref: Reference to peripheral object with operational block
            
        Returns:
            Dictionary of operational attribute name-value pairs
        """
        op = peripheral_ref.operational
        result = {
            "vcc": op.vcc,
            "ioVcc": getattr(op, "iovcc", op.vcc),
        }
        
        # Add power consumption if present
        if hasattr(op, "min") and op.min:
            result["power_min"] = {"value": op.min.value, "unit": op.min.unit}
        if hasattr(op, "max") and op.max:
            result["power_max"] = {"value": op.max.value, "unit": op.max.unit}
        if hasattr(op, "avg") and op.avg:
            result["power_avg"] = {"value": op.avg.value, "unit": op.avg.unit}
            
        # Add frequency if present
        if hasattr(op, "freq_max") and op.freq_max:
            result["freq_max"] = {"value": op.freq_max.value, "unit": op.freq_max.unit}
            
        return result
    
    def get_pin_mappings(self, connection, board) -> Dict[str, Any]:
        """Extract pin mappings from data connections.
        
        Args:
            connection: Connection object
            board: Board object for pin lookups
            
        Returns:
            Dictionary containing pin mappings and properties by connection type
        """
        pins = {}
        board_pins_map = {pin.name: pin for pin in board.pins}
        
        data_connections = connection.dataConns if hasattr(connection, 'dataConns') else connection
        
        for data_conn in data_connections:
            conn_type = data_conn.type
            
            if conn_type == "gpio":
                pins.update(self._extract_gpio_pins(connection, data_conn, board_pins_map))
            elif conn_type == "i2c":
                pins.update(self._extract_i2c_pins(connection, data_conn, board_pins_map))
            elif conn_type == "spi":
                pins.update(self._extract_spi_pins(connection, data_conn, board_pins_map))
            elif conn_type == "uart":
                pins.update(self._extract_uart_pins(connection, data_conn, board_pins_map))
            else:
                raise TypeError(f"Not a valid IO Connection Type: {conn_type}")
        
        return pins
    
    # ===== Helper Methods for Pin Extraction =====
    
    def _extract_gpio_pins(self, conn, data_conn, board_pins_map) -> Dict[str, Any]:
        """Extract GPIO pin mappings and properties."""
        pins = {}
        
        # Extract GPIO properties
        gpio_props = {}
        for prop in data_conn.props:
            if prop.name in ["mode", "pullup", "pulldown"]:
                gpio_props[prop.name] = self._convert_attribute_value(prop.value)
        
        # Handle pins based on peripheral pin name
        for pin_map in data_conn.pins:
            board_pin, periph_pin = self._get_board_and_periph_pins(conn, pin_map)
            pins[periph_pin] = board_pin
            pins[f"{periph_pin}_props"] = gpio_props
        
        return pins
    
    def _extract_i2c_pins(self, conn, data_conn, board_pins_map) -> Dict[str, Any]:
        """Extract I2C pin mappings, bus info, and properties."""
        pins = {}
        
        # Extract I2C properties
        i2c_props = {}
        for prop in data_conn.props:
            if prop.name in ["slave_address", "bus_speed"]:
                i2c_props[prop.name] = self._convert_attribute_value(prop.value)
        
        for pin_map in data_conn.pins:
            board_pin_name, periph_pin_name = self._get_board_and_periph_pins(conn, pin_map)
            board_pin = board_pins_map.get(board_pin_name)
            
            if pin_map.function == "sda":
                pins["sda"] = board_pin_name
                # Extract I2C bus from board pin's function definition
                if board_pin:
                    pins["i2c_bus"] = self._get_bus_from_pin(board_pin, "sda")
            elif pin_map.function == "scl":
                pins["scl"] = board_pin_name
            pins[f"{pin_map.function}_props"] = i2c_props
        
        return pins
    
    def _extract_spi_pins(self, conn, data_conn, board_pins_map) -> Dict[str, Any]:
        """Extract SPI pin mappings, bus info, and properties."""
        pins = {}
        
        # Extract SPI properties
        spi_props = {}
        for prop in data_conn.props:
            if prop.name in ["bus_speed", "mode"]:
                spi_props[prop.name] = self._convert_attribute_value(prop.value)
        
        for pin_map in data_conn.pins:
            board_pin_name, periph_pin_name = self._get_board_and_periph_pins(conn, pin_map)
            board_pin = board_pins_map.get(board_pin_name)
            
            if pin_map.function == "mosi":
                pins["mosi"] = board_pin_name
                # Extract SPI bus from board pin's function definition
                if board_pin:
                    pins["spi_bus"] = self._get_bus_from_pin(board_pin, "mosi")
            elif pin_map.function == "miso":
                pins["miso"] = board_pin_name
            elif pin_map.function == "sck":
                pins["sck"] = board_pin_name
            elif pin_map.function == "cs":
                pins["cs"] = board_pin_name
            pins[f"{pin_map.function}_props"] = spi_props
        
        return pins
    
    def _extract_uart_pins(self, conn, data_conn, board_pins_map) -> Dict[str, Any]:
        """Extract UART pin mappings, port info, and properties."""
        pins = {}
        
        # Extract UART properties
        uart_props = {}
        for prop in data_conn.props:
            if prop.name in ["baudrate", "parity", "stop_bits", "data_bits"]:
                uart_props[prop.name] = self._convert_attribute_value(prop.value)
        
        for pin_map in data_conn.pins:
            board_pin_name, periph_pin_name = self._get_board_and_periph_pins(conn, pin_map)
            board_pin = board_pins_map.get(board_pin_name)
            
            if pin_map.function == "tx":
                pins["tx"] = board_pin_name
                # Extract UART port from board pin's function definition
                if board_pin:
                    pins["uart_port"] = self._get_bus_from_pin(board_pin, "tx")
            elif pin_map.function == "rx":
                pins["rx"] = board_pin_name
            pins[f"{pin_map.function}_props"] = uart_props
        
        return pins

    def _get_board_and_periph_pins(self, conn, pin_map):
        """Helper to identify which pin is the board pin and which is the peripheral pin.
        """
        from_comp = conn.from_comp
        to_comp = conn.to_comp
        
        # Check if from_comp is the board
        is_from_board = False
        if hasattr(from_comp, 'ref'):
            if type(from_comp.ref).__name__ == 'BoardDef':
                is_from_board = True
        elif type(from_comp).__name__ == 'BoardDef':
            is_from_board = True
            
        if is_from_board:
            return pin_map.fromPin, pin_map.toPin
        else:
            return pin_map.toPin, pin_map.fromPin
    
    def _get_bus_from_pin(self, board_pin, function_type: str) -> int:
        """Extract bus/port number from board pin's function definition.
        
        Args:
            board_pin: Board pin object with funcs attribute
            function_type: Type of function to look for (e.g., 'sda', 'mosi', 'tx')
            
        Returns:
            Bus/port number as integer, defaults to 0 if not found
        """
        if hasattr(board_pin, 'funcs'):
            for func in board_pin.funcs:
                # Check if this function matches the type we're looking for
                if hasattr(func, 'ptype') and func.ptype == function_type:
                    # Return the bus number from the function definition
                    if hasattr(func, 'bus'):
                        return func.bus
        return 0
    
    def _convert_dict_attribute(self, dict_attr) -> Dict[str, Any]:
        """Convert DictAttribute object to Python dictionary.
        
        Args:
            dict_attr: DictAttribute object from model
            
        Returns:
            Python dictionary with attribute values
        """
        result = {}
        for item in dict_attr.items:
            result[item.key] = item.value
        return result
    
    def _convert_attribute_value(self, value) -> Any:
        """Convert AttributeValue to Python object.
        
        Args:
            value: AttributeValue object from model
            
        Returns:
            Python object (list, dict, or primitive)
        """
        v_type = type(value).__name__
        if v_type == "ListValue":
            return [self._convert_attribute_value(v) for v in value.items]
        elif v_type == "DictValue":
            return {item.key: self._convert_attribute_value(item.value) for item in value.items}
        elif v_type == "AttributeSet":
             return {attr.name: self._convert_attribute_value(attr.value) for attr in value.attributes}
        else:
            # VALUE (HEX, NUMBER, STRING, BOOL)
            if isinstance(value, str) and value.lower().startswith('0x'):
                try:
                    return int(value, 16)
                except ValueError:
                    return value
            return value
    

    
    # ===== Abstract Methods (Platform-Specific) =====
    
    @abstractmethod
    def generate(self) -> None:
        """Generate code for target platform.
        
        This method should orchestrate the entire code generation process,
        calling other generation methods as needed.
        """
        pass
    
    @abstractmethod
    def setup_template_environment(self) -> jinja2.Environment:
        """Setup Jinja2 environment with platform-specific templates.
        
        Returns:
            Configured Jinja2 Environment object
        """
        pass
