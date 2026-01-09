"""
Enhanced Validation Module for DeMoL
Based on formal semantics defined in SEMANTICS.md

This module implements:
- Well-formedness rules (Section 4 of SEMANTICS.md)
- Safety properties (Section 8.1 of SEMANTICS.md)
- Type checking (Section 7 of SEMANTICS.md)
- Constraint validation (Section 4.1 of SEMANTICS.md)
"""

from textx import get_location, TextXSemanticError
from typing import List, Set, Dict, Optional, Tuple
import re
import warnings

# Global lists to collect validation results during a single model processing run
_validation_errors = []
_validation_warnings = []
_passed_rules = []

def clear_validation_results():
    """Clear the collected validation results"""
    global _validation_errors, _validation_warnings, _passed_rules
    _validation_errors = []
    _validation_warnings = []
    _passed_rules = []

def get_validation_errors():
    """Get the list of collected validation errors"""
    return _validation_errors

def get_validation_warnings():
    """Get the list of collected validation warnings"""
    return _validation_warnings

def get_passed_rules():
    """Get the list of passed validation rules"""
    return _passed_rules

def report_passed_rule(rule_name: str, description: str = ""):
    """Record that a validation rule has passed successfully"""
    global _passed_rules
    _passed_rules.append({
        'name': rule_name,
        'description': description
    })


class ValidationError(TextXSemanticError):
    """Custom validation error with location information"""
    pass


def raise_validation_error(obj, msg: str, error_type: str = "Semantics"):
    """Collect a validation error with location information without terminating immediately"""
    global _validation_errors
    loc = get_location(obj)
    
    # Format the error message
    error_msg = f"[{error_type}] {msg}"
    
    _validation_errors.append({
        'obj': obj,
        'msg': error_msg,
        'loc': loc,
        'type': error_type
    })

def raise_validation_warning(obj, msg: str, warning_type: str = "Warning"):
    """Collect a validation warning with location information"""
    global _validation_warnings
    loc = get_location(obj)
    
    # Format the warning message
    warning_msg = f"[{warning_type}] {msg}"
    
    _validation_warnings.append({
        'obj': obj,
        'msg': warning_msg,
        'loc': loc,
        'type': warning_type
    })
    
    # Emit actual Python warning for tests/users
    warnings.warn(warning_msg, UserWarning)

def check_validation_errors(model, skip_semantics=False):
    """Check if any validation errors occurred and raise a single exception if they did"""
    global _validation_errors
    if _validation_errors and not skip_semantics:
        # Raise the first error to stop further processing and allow tests to match the message
        first_error = _validation_errors[0]['msg']
        raise ValidationError(first_error)


def get_connection_target(connection):
    """Helper to get the target object and its instance name from a connection"""
    if hasattr(connection, '_from_inst') and connection._from_inst:
        return connection._from_ref, connection._from_name
    if hasattr(connection, '_to_inst') and connection._to_inst:
        return connection._to_ref, connection._to_name
        
    # Fallback for older logic
    if hasattr(connection, 'target') and connection.target:
        target_obj = connection.target.target
        if target_obj:
            if hasattr(target_obj, 'ref'):
                return target_obj.ref, target_obj.name
            return target_obj, target_obj.name
    
    if hasattr(connection, 'peripheral') and connection.peripheral:
        return connection.peripheral.ref, connection.peripheral.name
        
    return None, "unknown"


def get_connection_endpoints(connection):
    """Helper to get both endpoints of a connection"""
    if hasattr(connection, '_from_ref'):
        return (connection._from_ref, connection._from_name, 
                connection._to_ref, connection._to_name)
    
    # Fallback
    target_ref, target_name = get_connection_target(connection)
    board = getattr(connection, 'board', None)
    return target_ref, target_name, board, board.name if board else "board"


# ============================================================================
# Power Connection Validation
# ============================================================================

def parse_voltage(power_type: str) -> Optional[float]:
    """
    Parse voltage from power type string.
    
    Examples:
        GND -> 0.0
        3V3 -> 3.3
        5V -> 5.0
        12V -> 12.0
        3.3V -> 3.3
        2.5V -> 2.5
    """
    if power_type is None:
        return None
    power_type_upper = str(power_type).upper()
    
    if power_type_upper == 'GND':
        return 0.0
    elif power_type_upper == '3V3':
        return 3.3
    elif power_type_upper == '5V':
        return 5.0
    elif power_type_upper == '12V':
        return 12.0
    
    # Try to parse custom voltage format like "3.3V" or "2.5V"
    match = re.match(r'(\d+\.?\d*)V?', power_type_upper)
    if match:
        return float(match.group(1))
    
    return None


def are_voltages_compatible(v1: float, v2: float, tolerance: float = 0.5) -> bool:
    """
    Check if two voltages are compatible.
    
    From SEMANTICS.md Section 4.1:
        compatible(v₁, v₂) ≡ (v₁ = v₂) ∨ (v₁ = Custom(x) ∧ v₂ = Custom(y) ∧ |x - y| ≤ 0.5)
    """
    return abs(v1 - v2) <= tolerance


def validate_power_connection(board_pin, peripheral_pin, connection) -> None:
    """
    Validate power connection compatibility.
    
    Implements rules from SEMANTICS.md Section 4.1:
    - [T-PowerConn-GND]: Both pins must be GND
    - [T-PowerConn-VCC]: Voltages must be compatible
    """
    board_voltage = parse_voltage(board_pin.ptype)
    peripheral_voltage = parse_voltage(peripheral_pin.ptype)
    
    if board_voltage is None:
        raise_validation_error(
            connection,
            f"Invalid board power pin type: {board_pin.ptype}",
            "PowerTypeError"
        )
    
    if peripheral_voltage is None:
        raise_validation_error(
            connection,
            f"Invalid peripheral power pin type: {peripheral_pin.ptype}",
            "PowerTypeError"
        )
    
    # Rule [T-PowerConn-GND]: Both GND
    if board_voltage == 0.0 and peripheral_voltage == 0.0:
        return  # Valid GND connection
    
    # Rule [T-PowerConn-VCC]: Non-GND voltages must be compatible
    if board_voltage != 0.0 and peripheral_voltage != 0.0:
        if not are_voltages_compatible(board_voltage, peripheral_voltage):
            raise_validation_error(
                connection,
                f"[Conn-Power] Incompatible power connection: board pin {board_pin.name} "
                f"({board_voltage}V) cannot connect to peripheral pin "
                f"{peripheral_pin.name} ({peripheral_voltage}V). "
                f"Voltage difference exceeds 0.5V tolerance.",
                "VoltageIncompatibilityError"
            )
        return
    
    # One is GND and the other is not - invalid
    raise_validation_error(
        connection,
        f"[Conn-Power] Cannot connect GND pin to power pin: board pin {board_pin.name} "
        f"({board_voltage}V) to peripheral pin {peripheral_pin.name} "
        f"({peripheral_voltage}V)",
        "PowerConnectionError"
    )


# ============================================================================
# Connection Validation
# ============================================================================

def get_pin_functions(pin) -> Set[str]:
    """Extract all function types from a pin"""
    functions = set()
    
    if not hasattr(pin, 'funcs'):
        return functions
    
    for func in pin.funcs:
        if hasattr(func, 'ptype'):
            # For I2C, SPI, UART, PWM functions with bus/channel
            functions.add(func.ptype)
        else:
            # For simple functions like GPIO, ADC, DAC
            functions.add('gpio')  # Default interpretation
    
    return functions


def validate_gpio_connection(board_pin, peripheral_pin, connection) -> None:
    """
    Validate GPIO connection.
    
    Implements [T-GPIO-Conn] from SEMANTICS.md Section 4.1:
        pin₁ : IOPin(_, _, funcs₁, _, _, _)    GPIO ∈ funcs₁
        pin₂ : IOPin(_, _, funcs₂, _, _, _)    GPIO ∈ funcs₂
    """
    board_funcs = get_pin_functions(board_pin)
    peripheral_funcs = get_pin_functions(peripheral_pin)
    
    # Check if both pins have GPIO functionality
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


def validate_i2c_connection(board_sda, board_scl, peripheral_sda, peripheral_scl, 
                           slave_addr: int, connection) -> None:
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


def validate_spi_connection(board_pins: Dict[str, object], peripheral_pins: Dict[str, object],
                           connection) -> None:
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


def validate_uart_connection(board_tx, board_rx, peripheral_tx, peripheral_rx,
                            baudrate, connection) -> None:
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


# ============================================================================
# Safety Properties
# ============================================================================

def validate_no_pin_conflicts(connections: List) -> None:
    """
    Validate Safety-Unique-Pins invariant.
    
    From SEMANTICS.md Section 6.7:
        Inv-Unique-Pins: ∀k₁, k₂ ∈ connections, k₁ ≠ k₂. usedPins(k₁) ∩ usedPins(k₂) = ∅
        
    EXCEPTION: 
    - I2C pins (SDA, SCL) can be shared (bus architecture).
    - Power pins (GND, VCC) can be shared (physically common nets).
    """
    # Map: pin_name -> List[Tuple[peripheral_name, usage_type]]
    board_pin_usage: Dict[str, List[Tuple[str, str]]] = {}
    
    for connection in connections:
        target_ref, target_name = get_connection_target(connection)
        
        # Collect all board pins used in this connection with their usage type
        # List of (pin_name, usage_type)
        used_pins: List[Tuple[str, str]] = []
        
        # Power connections
        for pconn in connection.powerConns:
            # Determine if it's GND or VCC based on pin name or type
            # We assume the board model has correct types, but here we just need a label
            # We can try to infer from the pin name or look up the board pin definition
            # For simplicity, we'll label it 'POWER' effectively allowing sharing
            # or better, check if it's GND.
            
            # To do this correctly, we should look up the pin on the board.
            # But we don't have easy access to the board object here without traversing.
            # However, validate_power_connection already checks types.
            # Let's assume 'GND' sharing is always allowed.
            # And 'VCC' sharing is allowed (parallel power).
            used_pins.append((pconn.fromPin, 'POWER'))
        
        # IO connections
        for data_conn in connection.dataConns:
            conn_type = data_conn.type
            
            for pin_map in data_conn.pins:
                if conn_type == 'gpio':
                    # GPIO uses PinConnection (no function attribute)
                    used_pins.append((pin_map.fromPin, 'GPIO'))
                elif conn_type == 'i2c':
                    # I2C uses PinMapping (has function attribute)
                    if pin_map.function == 'sda':
                        used_pins.append((pin_map.fromPin, 'I2C-SDA'))
                    elif pin_map.function == 'scl':
                        used_pins.append((pin_map.fromPin, 'I2C-SCL'))
                elif conn_type == 'spi':
                    if pin_map.function == 'mosi':
                        used_pins.append((pin_map.fromPin, 'SPI-MOSI'))
                    elif pin_map.function == 'miso':
                        used_pins.append((pin_map.fromPin, 'SPI-MISO'))
                    elif pin_map.function == 'sck':
                        used_pins.append((pin_map.fromPin, 'SPI-SCK'))
                    elif pin_map.function == 'cs':
                        used_pins.append((pin_map.fromPin, 'SPI-CS'))
                elif conn_type == 'uart':
                    if pin_map.function == 'tx':
                        used_pins.append((pin_map.fromPin, 'UART-TX'))
                    elif pin_map.function == 'rx':
                        used_pins.append((pin_map.fromPin, 'UART-RX'))
        
        # Check for conflicts
        for pin, usage in used_pins:
            if pin in board_pin_usage:
                # Check if sharing is allowed
                existing_usages = board_pin_usage[pin]
                
                for existing_peripheral, existing_usage in existing_usages:
                    # Allow sharing if:
                    # 1. Both are POWER (GND/VCC)
                    # 2. Both are I2C and same function (SDA=SDA, SCL=SCL)
                    
                    allowed = False
                    if usage == 'POWER' and existing_usage == 'POWER':
                        allowed = True
                    elif usage == existing_usage and usage.startswith('I2C-'):
                        allowed = True
                    
                    if not allowed:
                        raise_validation_error(
                            connection,
                            f"[Safety-Pin-Conflicts] Pin conflict detected: Board pin '{pin}' is already used by "
                            f"target '{existing_peripheral}' as '{existing_usage}'. "
                            f"Cannot reuse for target '{target_name}' as '{usage}'.",
                            "PinConflictError"
                        )
                
                # If we get here, sharing is allowed with all existing users
                board_pin_usage[pin].append((target_name, usage))
            else:
                board_pin_usage[pin] = [(target_name, usage)]


def validate_i2c_address_uniqueness(connections: List) -> None:
    """
    Validate Safety-I2C-Address-Unique property.
    
    From SEMANTICS.md Section 6.7:
        Inv-I2C-Address: On the same I2C bus, all slave addresses must be unique
    """
    i2c_addresses: Dict[int, List[str]] = {}
    
    for connection in connections:
        for data_conn in connection.dataConns:
            if data_conn.type == 'i2c':
                # Helper to get property value
                addr = None
                for p in data_conn.props:
                    if p.name == 'slave_address':
                        addr = p.value
                        if isinstance(addr, str) and addr.lower().startswith('0x'):
                            try:
                                addr = int(addr, 16)
                            except ValueError:
                                pass
                        break
                
                target_ref, target_name = get_connection_target(connection)
                
                if addr in i2c_addresses:
                    raise_validation_error(
                        connection,
                        f"[Safety-I2C-Address] I2C address conflict: Address 0x{addr:02X} is already used by "
                        f"target(s): {', '.join(i2c_addresses[addr])}. "
                        f"Cannot reuse for target '{target_name}'.",
                        "I2CAddressConflictError"
                    )
                else:
                    i2c_addresses.setdefault(addr, []).append(target_name)


def validate_voltage_limits(model) -> None:
    """
    Validate Safety-Voltage-Limits property.
    
    From SEMANTICS.md Section 8.1:
        Safety-Voltage-Limits: ∀k ∈ connections, p = k.peripheral.
            voltage(p) ≤ p.vcc.toVolts()
    """
    for connection in model.connections:
        target_ref, target_name = get_connection_target(connection)
        if target_ref is None or not hasattr(target_ref, 'operational'):
            continue
        
        if hasattr(target_ref.operational, 'vcc'):
            target_vcc_str = target_ref.operational.vcc
        elif hasattr(target_ref.operational, 'voltage'):
            target_vcc_str = target_ref.operational.voltage
        else:
            continue

        target_vcc = parse_voltage(target_vcc_str)
        
        if target_vcc is None:
            continue
        
        # Check if any power connections exceed peripheral's VCC rating
        for pconn in connection.powerConns:
            board_pin = next((p for p in model.components.board.pins 
                            if p.name == pconn.fromPin), None)
            if board_pin and hasattr(board_pin, 'ptype'):
                voltage = parse_voltage(board_pin.ptype)
                if voltage is not None and voltage > target_vcc + 0.5:
                    raise_validation_error(
                        pconn,
                        f"[Safety-Voltage-Limits] Voltage limit exceeded for target '{target_name}': "
                        f"Supplied voltage {voltage}V exceeds target's rated VCC of {target_vcc}V.",
                        "VoltageLimitError"
                    )


def validate_io_voltage_compatibility(model) -> None:
    """
    Validate IO Voltage Compatibility.
    
    Ensures that the board's IO voltage matches the peripheral's IO voltage
    to prevent communication errors or hardware damage.
    
    NOTE: This validation emits warnings rather than errors to allow
    validation to continue. Users should carefully review these warnings.
    
    Logic:
    - Board IO Voltage = board.ioVcc if set, else board.vcc
    - Peripheral IO Voltage = peripheral.ioVcc if set, else peripheral.vcc
    - Voltages must be compatible (within tolerance).
    """
    board = model.components.board
    
    # Determine Board IO Voltage
    board_io_vcc_str = board.operational.iovcc if hasattr(board.operational, 'iovcc') and board.operational.iovcc else board.operational.vcc
    board_iovcc = parse_voltage(board_io_vcc_str)
    
    if board_iovcc is None:
        # Should be caught by other validations, but safe to skip or warn
        return

    for connection in model.connections:
        target_ref, target_name = get_connection_target(connection)
        if target_ref is None or not hasattr(target_ref, 'operational') or not getattr(target_ref.operational, 'iovcc', None):
            continue
            
        target_iovcc = parse_voltage(target_ref.operational.iovcc)
        
        if target_iovcc is None:
            continue
            
        # Check compatibility
        if abs(board_iovcc - target_iovcc) > 0.5:
            raise_validation_warning(
                connection,
                f"[Safety-IO-Voltage] Board '{board.name}' operates at {board_iovcc}V (IO), "
                f"but target '{target_name}' operates at {target_iovcc}V (IO). "
                "This may cause communication errors or damage.",
                "IOVoltageWarning"
            )


def validate_common_ground(model) -> None:
    """
    Validate that peripheral and board share a common ground connection.
    
    Safety Property:
        Each peripheral should have at least one GND connection to the board
        to ensure proper electrical reference and circuit closure.

        When peripherals don't share a common ground with the board,
        which is important for electrical safety and signal integrity.
    
    This validation emits warnings rather than errors, as some peripherals
    may have alternative grounding through other means (e.g., USB connections).
    """
    for connection in model.connections:
        target_ref, target_name = get_connection_target(connection)
        if target_ref is None:
            continue
            
        # Check if there are any power connections
        if not hasattr(connection, 'powerConns') or not connection.powerConns:
            raise_validation_warning(
                connection,
                f"Target '{target_name}' has no power "
                f"connections to the board. Ensure proper grounding through external means "
                f"or add a GND power connection for electrical safety.",
                "WF-Common-Ground"
            )
            continue
        
        # Check if any power connection is GND
        has_gnd = False
        for pconn in connection.powerConns:
            # Get the board pin
            board_pin = next(
                (p for p in model.components.board.pins if p.name == pconn.fromPin),
                None
            )
            
            if board_pin and hasattr(board_pin, 'ptype'):
                board_voltage = parse_voltage(board_pin.ptype)
                if board_voltage == 0.0:  # GND connection
                    has_gnd = True
                    break
        
        # If no ground connection found, emit warning
        if not has_gnd:
            raise_validation_warning(
                connection,
                f"[Safety-Common-Ground] Target '{target_name}' does not have a common ground (GND) "
                "connection with the board. This is essential for signal integrity.",
                "CommonGroundWarning"
            )


def validate_power_paths(model) -> None:
    """
    Validate that all components requiring power have a path to a PowerSource.
    """
    # 1. Identify all PowerSources
    power_sources = {ps.name for ps in model.components.powerSources}
    
    # 2. Build a power graph
    # Nodes: Component names (Board, Peripherals, PowerSources)
    # Edges: Power connections (from_comp provides power to to_comp)
    power_graph = {} # target -> set of sources
    
    for conn in model.connections:
        if not hasattr(conn, 'powerConns') or not conn.powerConns:
            continue
        
        # Use horizontal logic: power flows from from_comp to to_comp
        from_ref, from_name, to_ref, to_name = get_connection_endpoints(conn)
        
        if from_ref is None or to_ref is None:
            continue
        
        # Determine power flow direction
        
        # Check if there is at least one voltage connection (not just GND)
        has_voltage = False
        for pconn in conn.powerConns:
            # We need to check the pin type of the source pin
            # But getting the pin object is complex here.
            # Simplified check: if pin name contains 'gnd' or 'GND', it's likely ground
            # This is a heuristic but matches our naming convention
            if 'gnd' not in pconn.fromPin.lower() and 'gnd' not in pconn.toPin.lower():
                has_voltage = True
                break
        
        if not has_voltage:
            continue

        # 1. PowerSource always provides power
        if from_name in power_sources:
            power_graph.setdefault(to_name, set()).add(from_name)
        elif to_name in power_sources:
            power_graph.setdefault(from_name, set()).add(to_name)
        # 2. Board provides power to Peripherals
        elif model.components.board:
            board_name = model.components.board.name
            if from_name == board_name:
                power_graph.setdefault(to_name, set()).add(from_name)
            elif to_name == board_name:
                power_graph.setdefault(from_name, set()).add(to_name)
            else:
                # Peripheral to Peripheral? Assume from -> to for now
                power_graph.setdefault(to_name, set()).add(from_name)
            
    # 3. Check reachability from any PowerSource
    def is_powered(node, visited=None):
        if node in power_sources:
            return True
        if visited is None:
            visited = set()
        if node in visited:
            return False
        visited.add(node)
        
        sources = power_graph.get(node, set())
        for s in sources:
            if is_powered(s, visited):
                return True
        return False

    # Check Board
    if model.components.board:
        board_name = model.components.board.name
        if not is_powered(board_name):
            raise_validation_warning(
                model.components.board,
                f"[Safety-Power-Path] Board '{board_name}' is not connected to any power source.",
                "MissingPowerSourceWarning"
            )
        
    # Check Peripherals
    for p in model.components.peripherals:
        if not is_powered(p.name):
             raise_validation_warning(
                p,
                f"[Safety-Power-Path] Peripheral '{p.name}' is not connected to any power source.",
                "MissingPowerSourceWarning"
            )

# ============================================================================
# Well-Formedness Validation
# ============================================================================

def validate_all_peripherals_connected(model) -> None:
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
            "UnconnectedPeripheralError"
        )
    
    if unconnected_sources:
        raise_validation_warning(
            model,
            f"[WF-Power-Sources-Connected] Unconnected power sources detected: {', '.join(unconnected_sources)}. "
            f"Power sources should be connected to the board or a peripheral.",
            "UnconnectedPowerSourceWarning"
        )


def validate_essential_pins_connected(model) -> None:
    """
    Validate that all pins marked as 'essential' in the peripheral definition
    are actually connected in the device model.
    """
    board = model.components.board
    
    for periph_def in model.components.peripherals:
        peripheral_ref = periph_def.ref
        # A pin is essential if 'optional' is NOT '?'
        essential_pins = [p for p in peripheral_ref.pins if getattr(p, 'optional', None) != '?']
        
        if not essential_pins:
            continue
            
        # Find all connections for this peripheral instance
        # Check both as target and as source
        connected_pin_names = set()
        for conn in model.connections:
            from_ref, from_name, to_ref, to_name = get_connection_endpoints(conn)
            
            # Determine if this peripheral is involved in this connection
            is_from_periph = (from_name == periph_def.name)
            is_to_periph = (to_name == periph_def.name)
            
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
                    "MissingEssentialConnectionError"
                )


def validate_broker_requirements(model) -> None:
    """
    Validate Inv-Broker-Connection.
    
    Broker is now mandatory for all models.
    """
    if not hasattr(model, 'broker') or model.broker is None:
        raise_validation_error(
            model,
            "[WF-Broker-Requirements] Broker configuration required: A broker must be defined in the model.",
            "MissingBrokerError"
        )

def validate_network_requirements(model) -> None:
    """
    Validate WF-Network-Requirements.
    
    Ensures that a network configuration is present.
    
    Network is now mandatory for all models.
    """
    if not hasattr(model, 'network') or model.network is None:
        raise_validation_error(
            model,
            "[WF-Network-Requirements] Network configuration required: A network must be configured in the model.",
            "MissingNetworkError"
        )


def validate_broker_security(model) -> None:
    """
    Validate Safety-Broker-Security property.
    
    From SEMANTICS.md Section 8.1 (implied safety):
        Remote brokers must have authentication configured to prevent unauthorized access.
    """
    if not hasattr(model, 'broker') or model.broker is None:
        return
        
    broker = model.broker
    host = getattr(broker, 'host', 'localhost')
    
    # Check if authentication is provided
    has_auth = False
    if hasattr(broker, 'auth') and broker.auth:
        # Check for username/password or API key
        username = getattr(broker.auth, "username", "")
        password = getattr(broker.auth, "password", "")
        key = getattr(broker.auth, "key", "")
        
        if (username and password) or key:
            has_auth = True
            
    if host != "localhost" and not has_auth:
        raise_validation_error(
            broker,
            f"Remote broker '{broker.name}' ({host}) is used without authentication. "
            "This is not secure. Please add 'auth.username' and 'auth.password' (or 'auth.key') to your broker configuration.",
            "SecurityError"
        )


def validate_unique_pin_numbers(component) -> None:
    """
    Validate WF-Unique-Pin-Numbers.
    
    Ensures that all pins defined in a component have unique pin numbers.
    """
    from typing import Dict, List # Added import for type hints
    pin_map: Dict[int, List[str]] = {}
    
    for pin in component.pins:
        if pin.number in pin_map:
            pin_map[pin.number].append(pin.name)
        else:
            pin_map[pin.number] = [pin.name]
            
    for pin_num, pin_names in pin_map.items():
        if len(pin_names) > 1:
            raise_validation_error(
                component,
                f"[WF-Unique-Pin-Numbers] Duplicate pin number {pin_num} used by pins: {', '.join(pin_names)}. "
                f"Pin numbers must be unique within a component.",
                "DuplicatePinNumberError"
            )


def validate_dependency_sources(component) -> None:
    """
    Validate that dependency source values are valid.
    
    Ensures that the 'source' field in dependencies only contains
    valid values: "pip" or "apt".
    """
    if not hasattr(component, 'dependencies') or not component.dependencies:
        return
    
    valid_sources = {"pip", "apt"}
    
    for dep_mapping in component.dependencies:
        if not hasattr(dep_mapping, 'items') or not dep_mapping.items:
            continue
            
        for item in dep_mapping.items:
            # Skip string-only dependencies (they don't have a source field)
            if isinstance(item, str):
                continue
                
            # Check if the item has a source field
            if hasattr(item, 'source') and item.source:
                source_value = item.source.strip('"').strip("'")
                
                if source_value not in valid_sources:
                    raise_validation_error(
                        component,
                        f"Invalid dependency source '{source_value}' for package '{item.name}'. "
                        f"Valid sources are: {', '.join(sorted(valid_sources))}",
                        "InvalidDependencySourceError"
                    )


def validate_connections(model) -> None:
    """
    Validate all connections in the model.
    
    Iterates over all connections and performs specific validations for
    power and data connections.
    """
    board = model.components.board
    
    # Get pin mappings
    board_pins_map = {p.name: p for p in board.pins}
    board_pin_names = set(board_pins_map.keys())
    
    # Also collect power sources for pin lookup
    power_sources_map = {ps.name: ps.ref for ps in model.components.powerSources}
    
    for c in model.connections:
        from_ref, from_name, to_ref, to_name = get_connection_endpoints(c)
        
        if from_ref is None or to_ref is None:
            continue
        
        # Determine which component is the board and which is the peripheral/power source
        # This is needed because pin connections are always written from the power source
        # perspective (board_pin -- peripheral_pin), regardless of CONNECT statement order
        is_from_board = (from_ref == board)
        is_to_board = (to_ref == board)
        
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
                    pconn,
                    f"Pin '{pconn.fromPin}' not found on '{from_name}'."
                )
                continue
            
            # Check if toPin exists on to_comp
            if pconn.toPin not in to_pin_names:
                raise_validation_error(
                    pconn,
                    f"Pin '{pconn.toPin}' not found on '{to_name}'."
                )
                continue
            
            from_pin_obj = from_pins_map[pconn.fromPin]
            to_pin_obj = to_pins_map[pconn.toPin]
            
            # Validate power connection (check voltage compatibility)
            if hasattr(from_pin_obj, 'ptype') and hasattr(to_pin_obj, 'ptype'):
                validate_power_connection(from_pin_obj, to_pin_obj, pconn)
        
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
                        if isinstance(val, str) and val.lower().startswith('0x'):
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
                        f"Source pin '{pin_map.fromPin}' not found on '{data_source_name}'."
                    )
                    pins_valid = False
                # Check if toPin exists on sink component
                if pin_map.toPin not in data_sink_pin_names:
                    raise_validation_error(
                        pin_map,
                        f"Target pin '{pin_map.toPin}' not found on '{data_sink_name}'."
                    )
                    pins_valid = False
            
            if not pins_valid:
                continue

            if conn_type == 'gpio':
                pin_conn = data_conn.pins[0] # Assuming single pin for GPIO for now
                
                # Enhanced validation: Check GPIO functionality
                source_pin = data_source_pins_map[pin_conn.fromPin]
                sink_pin = data_sink_pins_map[pin_conn.toPin]
                validate_gpio_connection(source_pin, sink_pin, data_conn)
                
            elif conn_type == 'i2c':
                sda = get_pin('sda')
                scl = get_pin('scl')
                slave_addr = get_prop('slave_address')

                if not sda or not scl:
                     # TODO: Better error handling for missing pins
                     continue
                
                # Enhanced validation: Check I2C functionality and address range
                source_sda = data_source_pins_map[sda.fromPin]
                source_scl = data_source_pins_map[scl.fromPin]
                sink_sda = data_sink_pins_map[sda.toPin]
                sink_scl = data_sink_pins_map[scl.toPin]
                validate_i2c_connection(
                    source_sda, source_scl, sink_sda, sink_scl,
                    slave_addr, data_conn
                )
                
            elif conn_type == 'spi':
                miso = get_pin('miso')
                mosi = get_pin('mosi')
                sck = get_pin('sck')
                cs = get_pin('cs')
                
                # Enhanced validation: Check SPI functionality
                source_spi_pins = {
                    'mosi': data_source_pins_map[mosi.fromPin] if mosi else None,
                    'miso': data_source_pins_map[miso.fromPin] if miso else None,
                    'sck': data_source_pins_map[sck.fromPin] if sck else None,
                    'cs': data_source_pins_map[cs.fromPin] if cs else None
                }
                sink_spi_pins = {
                    'mosi': data_sink_pins_map[mosi.toPin] if mosi else None,
                    'miso': data_sink_pins_map[miso.toPin] if miso else None,
                    'sck': data_sink_pins_map[sck.toPin] if sck else None,
                    'cs': data_sink_pins_map[cs.toPin] if cs else None
                }
                validate_spi_connection(source_spi_pins, sink_spi_pins, data_conn)
                
            elif conn_type == 'uart':
                tx = get_pin('tx')
                rx = get_pin('rx')
                baudrate = get_prop('baudrate')
                
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
                        pin_tx_source, pin_rx_source, pin_tx_sink, pin_rx_sink,
                        baudrate, data_conn
                    )
                elif is_to_board:
                    # Source is Peripheral, Sink is Board
                    validate_uart_connection(
                        pin_tx_sink, pin_rx_sink, pin_tx_source, pin_rx_source,
                        baudrate, data_conn
                    )
                else:
                    # Peripheral to Peripheral? Not supported by validate_uart_connection yet
                    # Or treat source as board?
                    pass


def validate_unique_peripheral_names(model) -> None:
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
                "DuplicatePeripheralNameError"
            )
        peripheral_names.add(name)


def validate_single_board(model) -> None:
    """
    Validate that exactly one board is used in the device model.
    
    Rule: A device can only have one board.
    Multiple boards or no boards will raise an error.
    """
    all_boards = []
    for use in model.uses:
        if hasattr(use, 'components') and use.components:
            for comp in use.components:
                if 'Board' in comp.ref.__class__.__name__:
                    all_boards.append(comp)
    
    if len(all_boards) == 0:
        raise_validation_error(
            model,
            "[WF-Single-Board] No board defined. Device must have exactly one board. "
            "Use 'USE <BoardModel>' to define the board.",
            "NoBoardError"
        )
    elif len(all_boards) > 1:
        raise_validation_error(
            model,
            f"[WF-Single-Board] Multiple boards defined ({len(all_boards)}). Device must have exactly one board.",
            "MultipleBoardsError"
        )


# ============================================================================
# Topic Validation
# ============================================================================

def validate_mqtt_topic(topic: str) -> Tuple[bool, Optional[str]]:
    """
    Validate MQTT topic format.
    
    Rules:
    - Use forward slashes (/) as level separators
    - Cannot be empty
    - Cannot start with $ (reserved for system topics)
    - Wildcards: + (single level), # (multi-level, must be last)
    - No null characters
    - Max level depth (typically 128, but we'll be lenient)
    
    Returns:
        (is_valid, error_message)
    """
    if not topic:
        return False, "MQTT topic cannot be empty"
    
    # Check for null characters
    if '\x00' in topic:
        return False, "MQTT topic cannot contain null characters"
    
    # Check length (MQTT spec allows up to 65535 bytes, but keep reasonable)
    if len(topic) > 1000:
        return False, f"MQTT topic too long ({len(topic)} chars), should be under 1000"
    
    # System topics start with $, which is reserved
    if topic.startswith('$'):
        return False, "MQTT topic cannot start with '$' (reserved for system topics)"
    
    # Check each level
    levels = topic.split('/')
    
    for i, level in enumerate(levels):
        # Single-level wildcard
        if level == '+':
            continue
        
        # Multi-level wildcard (must be last and alone)
        if '#' in level:
            if i != len(levels) - 1:
                return False, "MQTT wildcard '#' must be the last level"
            if level != '#':
                return False, "MQTT wildcard '#' must be alone in its level"
            continue
        
        # Regular level - check for invalid wildcard usage
        if '+' in level:
            if level != '+':
                return False, "MQTT wildcard '+' must be alone in its level"
    
    return True, None


def validate_amqp_topic(topic: str) -> Tuple[bool, Optional[str]]:
    """
    Validate AMQP routing key / topic format.
    
    Rules:
    - Use dots (.) as separators
    - Can use wildcards: * (single word), # (zero or more words)
    - Alphanumeric and underscore, hyphen, dot
    - Cannot be empty
    
    Returns:
        (is_valid, error_message)
    """
    if not topic:
        return False, "AMQP routing key cannot be empty"
    
    # Check length
    if len(topic) > 255:
        return False, f"AMQP routing key too long ({len(topic)} chars), should be under 255"
    
    # Split by dots
    parts = topic.split('.')
    
    for part in parts:
        if not part:
            return False, "AMQP routing key cannot have empty segments (double dots)"
        
        # Allow wildcards
        if part in ('*', '#'):
            continue
        
        # Check valid characters: alphanumeric, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', part):
            return False, f"AMQP routing key segment '{part}' contains invalid characters. Use alphanumeric, underscore, or hyphen only"
    
    return True, None


def validate_redis_topic(topic: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Redis pub/sub channel pattern.
    
    Rules:
    - Can use pattern matching with * and ?
    - Typically uses : or . as separators by convention
    - Cannot be empty
    - No special restrictions like MQTT
    
    Returns:
        (is_valid, error_message)
    """
    if not topic:
        return False, "Redis channel cannot be empty"
    
    # Check length
    if len(topic) > 512:
        return False, f"Redis channel too long ({len(topic)} chars), should be under 512"
    
    # Redis is quite flexible, just check it's not empty and reasonable length
    # Pattern matching with glob-style patterns is allowed
    
    return True, None


def validate_topic_format(model) -> None:
    """
    Validate that all connection topics match the broker type.
    
    Checks:
    - MQTT broker: topics use forward slashes
    - AMQP broker: topics use dots (routing keys)
    - Redis broker: flexible channel names
    """
    import warnings
    
    if not hasattr(model, 'broker') or not model.broker:
        # No broker defined, skip topic validation
        return
    
    broker = model.broker
    broker_type = broker.__class__.__name__  # AMQPBroker, MQTTBroker, or RedisBroker
    
    # Extract the actual type from the class name
    if 'MQTT' in broker_type.upper():
        validator = validate_mqtt_topic
        broker_name = "MQTT"
    elif 'AMQP' in broker_type.upper():
        validator = validate_amqp_topic
        broker_name = "AMQP"
    elif 'REDIS' in broker_type.upper():
        validator = validate_redis_topic
        broker_name = "Redis"
    else:
        # Unknown broker type, skip validation
        return
    
    # Validate each connection's topic
    for connection in model.connections:
        if not hasattr(connection, 'remote') or not connection.remote:
            continue
        
        topic = connection.remote.strip('"').strip("'")
        
        is_valid, error_msg = validator(topic)
        
        if not is_valid:
            location = get_location(connection)
            warning_msg = (
                f"[Topic-Validation] Invalid {broker_name} topic at "
                f"{location.get('filename', 'unknown')}:{location.get('line', '?')}: "
                f"Peripheral '{connection.peripheral.name}' has topic '{topic}'. "
                f"{error_msg}"
            )
            raise_validation_error(connection, warning_msg, "TopicValidationError")

def validate_board_ports(board) -> None:
    """
    Validate that the board's declared ports match the pin definitions.
    
    For each port type defined in the PORTS section (e.g., spi=2),
    verifies that there are corresponding pins defined with that function
    and bus index.
    """
    if not hasattr(board, 'ports') or not board.ports:
        return

    # Count available interfaces based on pin definitions
    available_interfaces = {
        'spi': set(),
        'i2c': set(),
        'uart': set(),
        'gpio': 0
    }

    for pin in board.pins:
        if hasattr(pin, 'funcs'):
            for func in pin.funcs:
                # Check for GPIO
                if hasattr(func, 'ptype') and func.ptype == 'gpio':
                    available_interfaces['gpio'] += 1
                
                # Check for SPI
                # SPI rule: ptype=SPIPinType "-" bus=INT
                if func.__class__.__name__ == 'SPI':
                    available_interfaces['spi'].add(func.bus)
                
                # Check for I2C
                elif func.__class__.__name__ == 'I2C':
                    available_interfaces['i2c'].add(func.bus)
                
                # Check for UART
                elif func.__class__.__name__ == 'UART':
                    available_interfaces['uart'].add(func.bus)

    # Validate declared ports against available interfaces
    for port in board.ports:
        port_name = port.name.lower()
        required_count = port.count

        if port_name == 'gpio':
            if available_interfaces['gpio'] < required_count:
                raise_validation_error(
                    board,
                    f"[WF-Board-Ports] Declared {required_count} GPIO pins, but only found {available_interfaces['gpio']} in PINS section.",
                    "PortCountMismatch"
                )
        elif port_name in ['spi', 'i2c', 'uart']:
            found_buses = len(available_interfaces[port_name])
            if found_buses < required_count:
                raise_validation_error(
                    board,
                    f"[WF-Board-Ports] Declared {required_count} {port_name.upper()} interfaces, but only found pins for {found_buses} buses in PINS section.",
                    "PortCountMismatch"
                )
        else:
            # For other custom ports, we might not have specific validation logic yet
            pass
