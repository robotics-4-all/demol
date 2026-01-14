"""Power connection validators.

This module contains validators for power-related semantic rules:
- Power connection compatibility (voltage matching, GND connections)
- Voltage limits (peripheral VCC ratings)
- IO voltage compatibility (board-peripheral communication voltage)
- Common ground validation
- Power path validation (ensuring components have power sources)
"""

from typing import Set
from ..core import raise_validation_error, raise_validation_warning
from ..utils import (
    get_connection_target,
    get_connection_endpoints,
    parse_voltage,
    are_voltages_compatible
)
from .base import BaseValidator


class PowerConnectionValidator(BaseValidator):
    """Validates power connection compatibility."""
    
    @staticmethod
    def get_name() -> str:
        return "Power Connection Validation"
    
    @staticmethod
    def get_description() -> str:
        return "Validates power connection compatibility (voltage matching, GND connections)"
    
    @staticmethod
    def validate(board_pin, peripheral_pin, connection):
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


class VoltageLimitsValidator(BaseValidator):
    """Validates that peripheral voltage limits are not exceeded."""
    
    @staticmethod
    def get_name() -> str:
        return "Voltage Limits Validation"
    
    @staticmethod
    def get_description() -> str:
        return "Ensures peripheral voltage limits (VCC ratings) are not exceeded"
    
    @staticmethod
    def validate(model):
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
            
            from_ref, from_name, to_ref, to_name = get_connection_endpoints(connection)
            is_from_board = (from_ref == model.components.board)

            # Check if any power connections exceed peripheral's VCC rating
            for pconn in connection.powerConns:
                board_pin_name = pconn.fromPin if is_from_board else pconn.toPin
                board_pin = next((p for p in model.components.board.pins 
                                if p.name == board_pin_name), None)
                if board_pin and hasattr(board_pin, 'ptype'):
                    voltage = parse_voltage(board_pin.ptype)
                    if voltage is not None and voltage > target_vcc + 0.5:
                        raise_validation_error(
                            pconn,
                            f"[Safety-Voltage-Limits] Voltage limit exceeded for target '{target_name}': "
                            f"Supplied voltage {voltage}V exceeds target's rated VCC of {target_vcc}V.",
                            "VoltageLimitError"
                        )


class IOVoltageCompatibilityValidator(BaseValidator):
    """Validates IO voltage compatibility between board and peripherals."""
    
    @staticmethod
    def get_name() -> str:
        return "IO Voltage Compatibility"
    
    @staticmethod
    def get_description() -> str:
        return "Ensures board IO voltage matches peripheral IO voltage for proper communication"
    
    @staticmethod
    def validate(model):
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


class CommonGroundValidator(BaseValidator):
    """Validates that peripherals share common ground with the board."""
    
    @staticmethod
    def get_name() -> str:
        return "Common Ground Validation"
    
    @staticmethod
    def get_description() -> str:
        return "Ensures peripherals have common ground connection with board for signal integrity"
    
    @staticmethod
    def validate(model):
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
            
            from_ref, from_name, to_ref, to_name = get_connection_endpoints(connection)
            is_from_board = (from_ref == model.components.board)
            
            # Check if any power connection is GND
            has_gnd = False
            for pconn in connection.powerConns:
                # Get the board pin name based on connection direction
                board_pin_name = pconn.fromPin if is_from_board else pconn.toPin
                
                # Get the board pin object
                board_pin = next(
                    (p for p in model.components.board.pins if p.name == board_pin_name),
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


class PowerPathValidator(BaseValidator):
    """Validates that all components have a path to a power source."""
    
    @staticmethod
    def get_name() -> str:
        return "Power Path Validation"
    
    @staticmethod
    def get_description() -> str:
        return "Ensures all components requiring power have a path to a PowerSource"
    
    @staticmethod
    def validate(model):
        """
        Validate that all components requiring power have a path to a PowerSource.
        """
        # 1. Identify all PowerSources
        power_sources = {ps.name for ps in model.components.powerSources}
        
        # 2. Build a power graph
        # Nodes: Component names (Board, Peripherals, PowerSources)
        # Edges: Power connections (from_comp provides power to to_comp)
        power_graph = {}  # target -> set of sources
        
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
            # 2. Board can provide power to peripherals
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


# Convenience function exports (for backward compatibility)
def validate_power_connection(board_pin, peripheral_pin, connection):
    """Validate power connection compatibility."""
    PowerConnectionValidator.validate(board_pin, peripheral_pin, connection)


def validate_voltage_limits(model):
    """Validate voltage limits."""
    VoltageLimitsValidator.validate(model)


def validate_io_voltage_compatibility(model):
    """Validate IO voltage compatibility."""
    IOVoltageCompatibilityValidator.validate(model)


def validate_common_ground(model):
    """Validate common ground."""
    CommonGroundValidator.validate(model)


def validate_power_paths(model):
    """Validate power paths."""
    PowerPathValidator.validate(model)


__all__ = [
    'PowerConnectionValidator',
    'VoltageLimitsValidator',
    'IOVoltageCompatibilityValidator',
    'CommonGroundValidator',
    'PowerPathValidator',
    'validate_power_connection',
    'validate_voltage_limits',
    'validate_io_voltage_compatibility',
    'validate_common_ground',
    'validate_power_paths',
]
