"""Board-specific validators.

This module contains validators for board-related semantic rules:
- Single board requirement
- Pin conflicts detection
- Unique pin numbers
- Board ports validation
"""

from typing import Dict, List
from ..core import raise_validation_error
from ..utils import get_connection_endpoints
from .base import BaseValidator


class SingleBoardValidator(BaseValidator):
    """Validates that exactly one board is used."""
    
    @staticmethod
    def get_name() -> str:
        return "Single Board Requirement"
    
    @staticmethod
    def get_description() -> str:
        return "Ensures device has exactly one board defined"
    
    @staticmethod
    def validate(model):
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


class PinConflictsValidator(BaseValidator):
    """Validates that board pins are not used in conflicting ways."""
    
    @staticmethod
    def get_name() -> str:
        return "Pin Conflicts Detection"
    
    @staticmethod
    def get_description() -> str:
        return "Ensures board pins are not used in conflicting ways (except allowed sharing)"
    
    @staticmethod
    def validate(model):
        """
        Validate Safety-Unique-Pins invariant.
        
        From SEMANTICS.md Section 6.7:
            Inv-Unique-Pins: ∀k₁, k₂ ∈ connections, k₁ ≠ k₂. usedPins(k₁) ∩ usedPins(k₂) = ∅
            
        EXCEPTION: 
        - I2C pins (SDA, SCL) can be shared (bus architecture).
        - Power pins (GND, VCC) can be shared (physically common nets).
        """
        # Map: pin_name -> List[Tuple[peripheral_name, usage_type]]
        board_pin_usage: Dict[str, List[tuple]] = {}
        
        board = model.components.board

        for connection in model.connections:
            from_ref, from_name, to_ref, to_name = get_connection_endpoints(connection)
            
            if from_ref is None or to_ref is None:
                continue

            is_from_board = (from_ref == board)
            is_to_board = (to_ref == board)
            
            # Determine target name (peripheral) for error reporting
            target_name = to_name if is_from_board else from_name

            # Collect all board pins used in this connection with their usage type
            # List of (pin_name, usage_type)
            used_pins: List[tuple] = []
            
            # Power connections
            for pconn in connection.powerConns:
                # Horizontal logic: fromPin on from_comp, toPin on to_comp
                board_pin = pconn.fromPin if is_from_board else pconn.toPin
                used_pins.append((board_pin, 'POWER'))
            
            # IO connections
            for data_conn in connection.dataConns:
                conn_type = data_conn.type
                
                for pin_map in data_conn.pins:
                    # Horizontal logic: fromPin on from_comp, toPin on to_comp
                    board_pin = pin_map.fromPin if is_from_board else pin_map.toPin
                    
                    if conn_type == 'gpio':
                        # GPIO uses PinConnection (no function attribute)
                        used_pins.append((board_pin, 'GPIO'))
                    elif conn_type == 'i2c':
                        # I2C uses PinMapping (has function attribute)
                        if pin_map.function == 'sda':
                            used_pins.append((board_pin, 'I2C-SDA'))
                        elif pin_map.function == 'scl':
                            used_pins.append((board_pin, 'I2C-SCL'))
                    elif conn_type == 'spi':
                        if pin_map.function == 'mosi':
                            used_pins.append((board_pin, 'SPI-MOSI'))
                        elif pin_map.function == 'miso':
                            used_pins.append((board_pin, 'SPI-MISO'))
                        elif pin_map.function == 'sck':
                            used_pins.append((board_pin, 'SPI-SCK'))
                        elif pin_map.function == 'cs':
                            used_pins.append((board_pin, 'SPI-CS'))
                    elif conn_type == 'uart':
                        if pin_map.function == 'tx':
                            used_pins.append((board_pin, 'UART-TX'))
                        elif pin_map.function == 'rx':
                            used_pins.append((board_pin, 'UART-RX'))
                    elif conn_type == 'pwm':
                        # PWM uses PinConnection (no function attribute)
                        used_pins.append((board_pin, 'PWM'))

            
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


class UniquePinNumbersValidator(BaseValidator):
    """Validates that pin numbers are unique within a component."""
    
    @staticmethod
    def get_name() -> str:
        return "Unique Pin Numbers"
    
    @staticmethod
    def get_description() -> str:
        return "Ensures all pins in a component have unique pin numbers"
    
    @staticmethod
    def validate(component):
        """
        Validate WF-Unique-Pin-Numbers.
        
        Ensures that all pins defined in a component have unique pin numbers.
        """
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


class BoardPortsValidator(BaseValidator):
    """Validates that board's declared ports match pin definitions."""
    
    @staticmethod
    def get_name() -> str:
        return "Board Ports Validation"
    
    @staticmethod
    def get_description() -> str:
        return "Ensures board's declared ports match the pin definitions"
    
    @staticmethod
    def validate(board):
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


# Convenience function exports (for backward compatibility)
def validate_single_board(model):
    """Validate single board requirement."""
    SingleBoardValidator.validate(model)


def validate_no_pin_conflicts(model):
    """Validate pin conflicts."""
    PinConflictsValidator.validate(model)


def validate_unique_pin_numbers(component):
    """Validate unique pin numbers."""
    UniquePinNumbersValidator.validate(component)


def validate_board_ports(board):
    """Validate board ports."""
    BoardPortsValidator.validate(board)


__all__ = [
    'SingleBoardValidator',
    'PinConflictsValidator',
    'UniquePinNumbersValidator',
    'BoardPortsValidator',
    'validate_single_board',
    'validate_no_pin_conflicts',
    'validate_unique_pin_numbers',
    'validate_board_ports',
]
