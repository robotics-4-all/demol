"""Communication protocol validators.

This module contains validators for data connection protocols:
- GPIO connections
- I2C connections (with address uniqueness)
- SPI connections
- UART connections
- PWM connections
- Connection orchestration
"""

from typing import Dict, Set
from ..core import raise_validation_error
from ..utils import get_pin_functions
from .base import BaseValidator


class GPIOConnectionValidator(BaseValidator):
    """Validates GPIO connections."""
    
    @staticmethod
    def get_name() -> str:
        return "GPIO Connection Validation"
    
    @staticmethod
    def get_description() -> str:
        return "Validates GPIO pin functionality and connection properties"
    
    @staticmethod
    def validate(board_pin, peripheral_pin, connection):
        """
        Validate GPIO connection.
        
        Checks:
        - Both pins have GPIO functionality
        - Valid properties (mode, pullup, pulldown)
        """
        board_funcs = get_pin_functions(board_pin)
        peripheral_funcs = get_pin_functions(peripheral_pin)
        
        if 'gpio' not in board_funcs and not any('gpio' in str(f).lower() for f in board_funcs):
            raise_validation_error(
                connection,
                f"[Conn-GPIO] Board pin {board_pin.name} does not have GPIO functionality. "
                f"Available functions: {', '.join(board_funcs)}",
                "GPIOFunctionError"
            )
        
        if 'gpio' not in peripheral_funcs and not any('gpio' in str(f).lower() for f in peripheral_funcs):
            raise_validation_error(
                connection,
                f"[Conn-GPIO] Peripheral pin {peripheral_pin.name} does not have GPIO functionality. "
                f"Available functions: {', '.join(peripheral_funcs)}",
                "GPIOFunctionError"
            )
        
        # Validate properties
        valid_props = {'mode', 'pullup', 'pulldown'}
        for prop in connection.props:
            if prop.name == 'name':
                raise_validation_error(
                    connection,
                    f"[Conn-GPIO] Property 'name' is deprecated for GPIO connections. "
                    f"Use 'mode', 'pullup', or 'pulldown' instead.",
                    "DeprecatedPropertyError"
                )
            if prop.name not in valid_props:
                raise_validation_error(
                    connection,
                    f"[Conn-GPIO] Invalid property '{prop.name}' for GPIO connection. "
                    f"Valid properties are: {', '.join(valid_props)}",
                    "InvalidPropertyError"
                )
            
            if prop.name == 'mode':
                if prop.value not in ['input', 'output']:
                    raise_validation_error(
                        connection,
                        f"[Conn-GPIO] Invalid mode '{prop.value}'. Must be 'input' or 'output'.",
                        "InvalidModeError"
                    )
            elif prop.name in ['pullup', 'pulldown']:
                if not isinstance(prop.value, bool):
                    raise_validation_error(
                        connection,
                        f"[Conn-GPIO] Property '{prop.name}' must be a boolean.",
                        "InvalidTypeError"
                    )


class I2CConnectionValidator(BaseValidator):
    """Validates I2C connections."""
    
    @staticmethod
    def get_name() -> str:
        return "I2C Connection Validation"
    
    @staticmethod
    def get_description() -> str:
        return "Validates I2C pin functionality, slave addresses, and bus configuration"
    
    @staticmethod
    def validate(board_sda, board_scl, peripheral_sda, peripheral_scl, 
                slave_addr: int, connection):
        """
        Validate I2C connection.
        
        Implements [T-I2C-Conn] from SEMANTICS.md Section 4.1:
            - Board pins must have SDA/SCL functions
            - Peripheral pins must have SDA/SCL functions
            - Slave address must be in range 0x00-0x7F
        """
        # Validate properties
        valid_props = {'slave_address', 'bus_speed'}
        for prop in connection.props:
            if prop.name == 'name':
                raise_validation_error(
                    connection,
                    f"[Conn-I2C] Property 'name' is deprecated for I2C connections. "
                    f"Use 'slave_address' or 'bus_speed' instead.",
                    "DeprecatedPropertyError"
                )
            if prop.name not in valid_props:
                raise_validation_error(
                    connection,
                    f"[Conn-I2C] Invalid property '{prop.name}' for I2C connection. "
                    f"Valid properties are: {', '.join(valid_props)}",
                    "InvalidPropertyError"
                )
            
            if prop.name == 'bus_speed':
                if not isinstance(prop.value, int) or prop.value <= 0:
                    raise_validation_error(
                        connection,
                        f"[Conn-I2C] Property 'bus_speed' must be a positive integer.",
                        "InvalidValueError"
                    )

        # Validate slave address range
        if not (0x00 <= slave_addr <= 0x7F):
            raise_validation_error(
                connection,
                f"[Conn-I2C] I2C slave address 0x{slave_addr:02X} out of valid range [0x00-0x7F]",
                "I2CAddressError"
            )
        
        # Check board SDA pin
        board_sda_funcs = get_pin_functions(board_sda)
        if not any('sda' in str(f).lower() for f in board_sda_funcs):
            raise_validation_error(
                connection,
                f"[Conn-I2C] Board pin {board_sda.name} does not have SDA (I2C) functionality",
                "I2CFunctionError"
            )
        
        # Check board SCL pin
        board_scl_funcs = get_pin_functions(board_scl)
        if not any('scl' in str(f).lower() for f in board_scl_funcs):
            raise_validation_error(
                connection,
                f"[Conn-I2C] Board pin {board_scl.name} does not have SCL (I2C) functionality",
                "I2CFunctionError"
            )
        
        # Check peripheral SDA pin
        peripheral_sda_funcs = get_pin_functions(peripheral_sda)
        if not any('sda' in str(f).lower() for f in peripheral_sda_funcs):
            raise_validation_error(
                connection,
                f"[Conn-I2C] Peripheral pin {peripheral_sda.name} does not have SDA (I2C) functionality",
                "I2CFunctionError"
            )
        
        # Check peripheral SCL pin
        peripheral_scl_funcs = get_pin_functions(peripheral_scl)
        if not any('scl' in str(f).lower() for f in peripheral_scl_funcs):
            raise_validation_error(
                connection,
                f"[Conn-I2C] Peripheral pin {peripheral_scl.name} does not have SCL (I2C) functionality",
                "I2CFunctionError"
            )


class I2CAddressUniquenessValidator(BaseValidator):
    """Validates I2C address uniqueness on each bus."""
    
    @staticmethod
    def get_name() -> str:
        return "I2C Address Uniqueness"
    
    @staticmethod
    def get_description() -> str:
        return "Ensures I2C slave addresses are unique per bus"
    
    @staticmethod
    def validate(model_or_connections):
        """
        Validate I2C address uniqueness.
        
        Ensures that each I2C slave address is unique on a given bus.
        Multiple peripherals can share the same address if they are on different buses.
        
        Args:
            model_or_connections: Either a full model object or a list of connections
        """
        from ..utils import get_connection_target, get_connection_endpoints
        
        # Handle both model object and connections list for backward compatibility
        if hasattr(model_or_connections, 'connections'):
            # It's a model object
            model = model_or_connections
            connections = model.connections
        else:
            # It's a connections list
            connections = model_or_connections
            model = None
        
        # Track I2C addresses per bus
        # Key: (board_sda_pin, board_scl_pin) tuple representing the bus
        # Value: dict of {address: [peripheral_names]}
        i2c_buses = {}
        
        for connection in connections:
            if not hasattr(connection, 'dataConns') or not connection.dataConns:
                continue
            
            for dconn in connection.dataConns:
                if dconn.type != 'i2c':
                    continue
                
                # Extract slave address
                addr = None
                for prop in dconn.props:
                    if prop.name == 'slave_address':
                        addr = prop.value
                        if isinstance(addr, str) and addr.lower().startswith('0x'):
                            try:
                                addr = int(addr, 16)
                            except ValueError:
                                pass
                        break
                
                if addr is None:
                    continue
                
                # Get SDA and SCL pin mappings
                sda_pin = None
                scl_pin = None
                for pin_map in dconn.pins:
                    if hasattr(pin_map, 'function'):
                        if pin_map.function == 'sda':
                            sda_pin = pin_map
                        elif pin_map.function == 'scl':
                            scl_pin = pin_map
                
                if not sda_pin or not scl_pin:
                    continue
                
                # Identify the bus by the board pins
                from_ref, from_name, to_ref, to_name = get_connection_endpoints(connection)
                
                # Determine which side is the board
                if model is not None:
                    is_from_board = (from_ref == model.components.board)
                else:
                    # Fallback: assume fromPin is board pin
                    is_from_board = True
                
                # Get the board pins for this bus
                if is_from_board:
                    bus_key = (sda_pin.fromPin, scl_pin.fromPin)
                else:
                    bus_key = (sda_pin.toPin, scl_pin.toPin)
                
                target_ref, target_name = get_connection_target(connection)
                
                # Check for address conflict on this bus
                if bus_key not in i2c_buses:
                    i2c_buses[bus_key] = {}
                
                if addr in i2c_buses[bus_key]:
                    existing_targets = i2c_buses[bus_key][addr]
                    raise_validation_error(
                        dconn,
                        f"[Safety-I2C-Address] I2C address conflict: Address 0x{addr:02X} is already used by "
                        f"target(s): {', '.join(existing_targets)} on the same bus (SDA={bus_key[0]}, SCL={bus_key[1]}). "
                        f"Cannot reuse for target '{target_name}'.",
                        "I2CAddressConflictError"
                    )
                else:
                    i2c_buses[bus_key].setdefault(addr, []).append(target_name)


class SPIConnectionValidator(BaseValidator):
    """Validates SPI connections."""
    
    @staticmethod
    def get_name() -> str:
        return "SPI Connection Validation"
    
    @staticmethod
    def get_description() -> str:
        return "Validates SPI pin functionality and bus configuration"
    
    @staticmethod
    def validate(board_pins: Dict[str, object], peripheral_pins: Dict[str, object],
                connection):
        """
        Validate SPI connection.
        
        Checks that all required SPI pins (MOSI, MISO, SCK, CS) have appropriate functionality.
        """
        # Validate properties
        valid_props = {'bus_speed', 'mode'}
        for prop in connection.props:
            if prop.name == 'name':
                raise_validation_error(
                    connection,
                    f"[Conn-SPI] Property 'name' is deprecated for SPI connections. "
                    f"Use 'bus_speed' or 'mode' instead.",
                    "DeprecatedPropertyError"
                )
            if prop.name not in valid_props:
                raise_validation_error(
                    connection,
                    f"[Conn-SPI] Invalid property '{prop.name}' for SPI connection. "
                    f"Valid properties are: {', '.join(valid_props)}",
                    "InvalidPropertyError"
                )
            
            if prop.name == 'bus_speed':
                if not isinstance(prop.value, int) or prop.value <= 0:
                    raise_validation_error(
                        connection,
                        f"[Conn-SPI] Property 'bus_speed' must be a positive integer.",
                        "InvalidValueError"
                    )
            elif prop.name == 'mode':
                if not isinstance(prop.value, int) or prop.value not in [0, 1, 2, 3]:
                    raise_validation_error(
                        connection,
                        f"[Conn-SPI] Property 'mode' must be an integer between 0 and 3.",
                        "InvalidValueError"
                    )

        spi_pin_types = ['mosi', 'miso', 'sck', 'cs']
        
        for pin_type in spi_pin_types:
            # Check board pin
            board_pin = board_pins[pin_type]
            board_funcs = get_pin_functions(board_pin)
            if not any(pin_type in str(f).lower() for f in board_funcs):
                raise_validation_error(
                    connection,
                    f"[Conn-SPI] Board pin {board_pin.name} does not have {pin_type.upper()} (SPI) functionality",
                    "SPIFunctionError"
                )
            
            # Check peripheral pin
            peripheral_pin = peripheral_pins[pin_type]
            peripheral_funcs = get_pin_functions(peripheral_pin)
            if not any(pin_type in str(f).lower() for f in peripheral_funcs):
                raise_validation_error(
                    connection,
                    f"[Conn-SPI] Peripheral pin {peripheral_pin.name} does not have {pin_type.upper()} (SPI) functionality",
                    "SPIFunctionError"
                )


class UARTConnectionValidator(BaseValidator):
    """Validates UART connections."""
    
    @staticmethod
    def get_name() -> str:
        return "UART Connection Validation"
    
    @staticmethod
    def get_description() -> str:
        return "Validates UART TX/RX pin functionality and communication parameters"
    
    @staticmethod
    def validate(board_tx, board_rx, peripheral_tx, peripheral_rx,
                baudrate, connection):
        """
        Validate UART connection.
        
        Checks:
        - TX/RX pin functionality
        - Valid baudrate (common values)
        """
        # Validate properties
        valid_props = {'baudrate', 'parity', 'stop_bits', 'data_bits'}
        for prop in connection.props:
            if prop.name == 'name':
                raise_validation_error(
                    connection,
                    f"[Conn-UART] Property 'name' is deprecated for UART connections. "
                    f"Use 'baudrate', 'parity', 'stop_bits', or 'data_bits' instead.",
                    "DeprecatedPropertyError"
                )
            if prop.name not in valid_props:
                raise_validation_error(
                    connection,
                    f"[Conn-UART] Invalid property '{prop.name}' for UART connection. "
                    f"Valid properties are: {', '.join(valid_props)}",
                    "InvalidPropertyError"
                )
            
            if prop.name == 'baudrate':
                # Accept both int and float (as long as it's a whole number and positive)
                if isinstance(prop.value, (int, float)):
                    if isinstance(prop.value, float) and not prop.value.is_integer():
                        raise_validation_error(
                            connection,
                            f"[Conn-UART] Property 'baudrate' must be a whole number, got {prop.value}.",
                            "InvalidValueError"
                        )
                    if prop.value <= 0:
                        raise_validation_error(
                            connection,
                            f"[Conn-UART] Property 'baudrate' must be positive, got {prop.value}.",
                            "InvalidValueError"
                        )
                else:
                    raise_validation_error(
                        connection,
                        f"[Conn-UART] Property 'baudrate' must be a positive integer.",
                        "InvalidValueError"
                    )
            elif prop.name == 'parity':
                if prop.value not in ['none', 'even', 'odd', 'mark', 'space']:
                    raise_validation_error(
                        connection,
                        f"[Conn-UART] Invalid parity '{prop.value}'. Must be 'none', 'even', 'odd', 'mark', or 'space'.",
                        "InvalidValueError"
                    )
            elif prop.name == 'stop_bits':
                if prop.value not in [1, 2]:
                    raise_validation_error(
                        connection,
                        f"[Conn-UART] Invalid stop_bits '{prop.value}'. Must be 1 or 2.",
                        "InvalidValueError"
                    )
            elif prop.name == 'data_bits':
                if prop.value not in [5, 6, 7, 8]:
                    raise_validation_error(
                        connection,
                        f"[Conn-UART] Invalid data_bits '{prop.value}'. Must be 5, 6, 7, or 8.",
                        "InvalidValueError"
                    )

        # Validate baudrate
        # Convert to int if it's a float representing a whole number
        if isinstance(baudrate, float):
            baudrate = int(baudrate)
        
        valid_baudrates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
        if baudrate not in valid_baudrates:
            raise_validation_error(
                connection,
                f"[Conn-UART] Unusual UART baudrate {baudrate}. Common values: {valid_baudrates}",
                "UARTBaudrateWarning"
            )
        
        # Check TX connection (Board TX -> Peripheral RX)
        board_tx_funcs = get_pin_functions(board_tx)
        if not any('tx' in str(f).lower() for f in board_tx_funcs):
            raise_validation_error(
                connection,
                f"[Conn-UART] Board pin {board_tx.name} does not have TX (UART) functionality",
                "UARTFunctionError"
            )
        
        peripheral_tx_funcs = get_pin_functions(peripheral_tx)
        if not any('rx' in str(f).lower() for f in peripheral_tx_funcs):
            raise_validation_error(
                connection,
                f"[Conn-UART] Peripheral pin {peripheral_tx.name} does not have RX (UART) functionality. "
                f"UART requires connecting Board TX to Peripheral RX.",
                "UARTFunctionError"
            )
        
        # Check RX connection (Board RX <- Peripheral TX)
        board_rx_funcs = get_pin_functions(board_rx)
        if not any('rx' in str(f).lower() for f in board_rx_funcs):
            raise_validation_error(
                connection,
                f"[Conn-UART] Board pin {board_rx.name} does not have RX (UART) functionality",
                "UARTFunctionError"
            )
        
        peripheral_rx_funcs = get_pin_functions(peripheral_rx)
        if not any('tx' in str(f).lower() for f in peripheral_rx_funcs):
            raise_validation_error(
                connection,
                f"[Conn-UART] Peripheral pin {peripheral_rx.name} does not have TX (UART) functionality. "
                f"UART requires connecting Board RX to Peripheral TX.",
                "UARTFunctionError"
            )


class PWMConnectionValidator(BaseValidator):
    """Validates PWM connections."""
    
    @staticmethod
    def get_name() -> str:
        return "PWM Connection Validation"
    
    @staticmethod
    def get_description() -> str:
        return "Validates PWM pin functionality and signal parameters"
    
    @staticmethod
    def validate(board_pin, peripheral_pin, connection):
        """
        Validate PWM connection.
        
        Checks:
        - Board pin has PWM functionality
        - Peripheral pin can accept PWM (IO pin)
        - Valid PWM properties (frequency, duty_cycle, channel)
        """
        # Validate properties
        valid_props = {'frequency', 'duty_cycle', 'channel'}
        for prop in connection.props:
            if prop.name not in valid_props:
                raise_validation_error(
                    connection,
                    f"[Conn-PWM] Invalid property '{prop.name}' for PWM connection. "
                    f"Valid properties are: {', '.join(valid_props)}",
                    "InvalidPropertyError"
                )
            
            if prop.name == 'frequency':
                if not isinstance(prop.value, (int, float)) or prop.value <= 0:
                    raise_validation_error(
                        connection,
                        f"[Conn-PWM] Property 'frequency' must be a positive number.",
                        "InvalidValueError"
                    )
            elif prop.name == 'duty_cycle':
                if not isinstance(prop.value, (int, float)) or not (0 <= prop.value <= 100):
                    raise_validation_error(
                        connection,
                        f"[Conn-PWM] Property 'duty_cycle' must be a number between 0 and 100.",
                        "InvalidValueError"
                    )
            elif prop.name == 'channel':
                if not isinstance(prop.value, int) or prop.value < 0:
                    raise_validation_error(
                        connection,
                        f"[Conn-PWM] Property 'channel' must be a non-negative integer.",
                        "InvalidValueError"
                    )
        
        # Check board pin has PWM functionality
        board_funcs = get_pin_functions(board_pin)
        if not any('pwm' in str(f).lower() for f in board_funcs):
            raise_validation_error(
                connection,
                f"[Conn-PWM] Board pin {board_pin.name} does not have PWM functionality. "
                f"Available functions: {', '.join(board_funcs)}",
                "PWMFunctionError"
            )
        
        # Check peripheral pin is an IO pin (can accept PWM signal)
        # PWM peripherals typically have gpio or pwm functionality
        peripheral_funcs = get_pin_functions(peripheral_pin)
        if not peripheral_funcs:
            # If no functions defined, assume it's a generic IO pin
            return
        
        # Check if pin can accept PWM (either has pwm or gpio functionality)
        has_io_capability = any(
            'pwm' in str(f).lower() or 'gpio' in str(f).lower() 
            for f in peripheral_funcs
        )
        
        if not has_io_capability:
            raise_validation_error(
                connection,
                f"[Conn-PWM] Peripheral pin {peripheral_pin.name} cannot accept PWM signals. "
                f"Available functions: {', '.join(peripheral_funcs)}",
                "PWMFunctionError"
            )


# Convenience function exports (for backward compatibility)
def validate_gpio_connection(board_pin, peripheral_pin, connection):
    """Validate GPIO connection."""
    GPIOConnectionValidator.validate(board_pin, peripheral_pin, connection)


def validate_i2c_connection(board_sda, board_scl, peripheral_sda, peripheral_scl, 
                           slave_addr: int, connection):
    """Validate I2C connection."""
    I2CConnectionValidator.validate(board_sda, board_scl, peripheral_sda, peripheral_scl, 
                                   slave_addr, connection)


def validate_i2c_address_uniqueness(model):
    """Validate I2C address uniqueness."""
    I2CAddressUniquenessValidator.validate(model)


def validate_spi_connection(board_pins: Dict[str, object], peripheral_pins: Dict[str, object],
                           connection):
    """Validate SPI connection."""
    SPIConnectionValidator.validate(board_pins, peripheral_pins, connection)


def validate_uart_connection(board_tx, board_rx, peripheral_tx, peripheral_rx,
                            baudrate, connection):
    """Validate UART connection."""
    UARTConnectionValidator.validate(board_tx, board_rx, peripheral_tx, peripheral_rx,
                                    baudrate, connection)


def validate_pwm_connection(board_pin, peripheral_pin, connection):
    """Validate PWM connection."""
    PWMConnectionValidator.validate(board_pin, peripheral_pin, connection)


__all__ = [
    'GPIOConnectionValidator',
    'I2CConnectionValidator',
    'I2CAddressUniquenessValidator',
    'SPIConnectionValidator',
    'UARTConnectionValidator',
    'PWMConnectionValidator',
    'validate_gpio_connection',
    'validate_i2c_connection',
    'validate_i2c_address_uniqueness',
    'validate_spi_connection',
    'validate_uart_connection',
    'validate_pwm_connection',
]
