"""
Utility Functions for DeMoL Validation

This module provides helper functions used across validators.
"""

from typing import Set, Optional
import re


def get_connection_target(connection):
    """Helper to get the target object and its instance name from a connection."""
    board = getattr(connection, 'board', None)
    
    from_inst = getattr(connection, '_from_inst', None)
    from_ref = getattr(connection, '_from_ref', None)
    from_name = getattr(connection, '_from_name', "unknown")
    
    to_inst = getattr(connection, '_to_inst', None)
    to_ref = getattr(connection, '_to_ref', None)
    to_name = getattr(connection, '_to_name', "unknown")
    
    # Prefer peripheral (non-board) instance
    if from_inst and from_ref != board:
        return from_ref, from_name
    if to_inst and to_ref != board:
        return to_ref, to_name
        
    # Fallback to from_inst if both are board or none are board
    if from_inst:
        return from_ref, from_name
    if to_inst:
        return to_ref, to_name
        
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
    """Helper to get both endpoints of a connection."""
    if hasattr(connection, '_from_ref'):
        return (connection._from_ref, connection._from_name, 
                connection._to_ref, connection._to_name)
    
    # Fallback
    target_ref, target_name = get_connection_target(connection)
    board = getattr(connection, 'board', None)
    return target_ref, target_name, board, board.name if board else "board"


def get_pin_functions(pin) -> Set[str]:
    """Extract all function types from a pin."""
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
