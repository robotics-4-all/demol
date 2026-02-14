"""Semantic validation framework for DeMoL.

This package provides comprehensive semantic validation for DeMoL models,
organized into logical categories for better maintainability and extensibility.

The validation framework is built around:
- Core infrastructure (error/warning collection, reporting)
- Helper utilities (voltage parsing, pin functions, etc.)
- Categorized validators (power, communication, peripheral, board, device, general)

All validators follow a consistent class-based pattern inheriting from BaseValidator,
while maintaining backward compatibility through function exports.
"""

# Core infrastructure
from .core import (
    clear_validation_results,
    get_validation_errors,
    get_validation_warnings,
    get_passed_rules,
    report_passed_rule,
    raise_validation_error,
    raise_validation_warning,
    check_validation_errors,
    ValidationError,
    get_location,
)

# Helper utilities
from .utils import (
    get_connection_target,
    get_connection_endpoints,
    get_pin_functions,
    parse_voltage,
    are_voltages_compatible,
)

# Power validators
from .validators.power import (
    PowerConnectionValidator,
    VoltageLimitsValidator,
    IOVoltageCompatibilityValidator,
    CommonGroundValidator,
    PowerPathValidator,
    validate_power_connection,
    validate_voltage_limits,
    validate_io_voltage_compatibility,
    validate_common_ground,
    validate_power_paths,
)

# Communication validators
from .validators.communication import (
    GPIOConnectionValidator,
    I2CConnectionValidator,
    I2CAddressUniquenessValidator,
    SPIConnectionValidator,
    UARTConnectionValidator,
    PWMConnectionValidator,
    validate_gpio_connection,
    validate_i2c_connection,
    validate_i2c_address_uniqueness,
    validate_spi_connection,
    validate_uart_connection,
    validate_pwm_connection,
)

# Peripheral validators
from .validators.peripheral import (
    PeripheralConnectivityValidator,
    EssentialPinsValidator,
    UniquePeripheralNamesValidator,
    validate_all_peripherals_connected,
    validate_essential_pins_connected,
    validate_unique_peripheral_names,
)

# Board validators
from .validators.board import (
    SingleBoardValidator,
    PinConflictsValidator,
    UniquePinNumbersValidator,
    BoardPortsValidator,
    validate_single_board,
    validate_no_pin_conflicts,
    validate_unique_pin_numbers,
    validate_board_ports,
)

# Device validators
from .validators.device import (
    BrokerRequirementsValidator,
    NetworkRequirementsValidator,
    BrokerSecurityValidator,
    TopicFormatValidator,
    validate_broker_requirements,
    validate_network_requirements,
    validate_broker_security,
    validate_topic_format,
    validate_mqtt_topic,
    validate_amqp_topic,
    validate_redis_topic,
)

# General validators
from .validators.general import (
    DependencySourcesValidator,
    ConnectionsOrchestratorValidator,
    validate_dependency_sources,
    validate_connections,
)

# SmartConnect validators
from .validators.smart_connection import (
    SmartConnectValidator,
    validate_smart_connections,
)

# Base validator class
from .validators.base import BaseValidator

__all__ = [
    # Core infrastructure
    "clear_validation_results",
    "get_validation_errors",
    "get_validation_warnings",
    "get_passed_rules",
    "report_passed_rule",
    "raise_validation_error",
    "raise_validation_warning",
    "check_validation_errors",
    "ValidationError",
    "get_location",
    # Helper utilities
    "get_connection_target",
    "get_connection_endpoints",
    "get_pin_functions",
    "parse_voltage",
    "are_voltages_compatible",
    # Validator classes
    "BaseValidator",
    # Power validators
    "PowerConnectionValidator",
    "VoltageLimitsValidator",
    "IOVoltageCompatibilityValidator",
    "CommonGroundValidator",
    "PowerPathValidator",
    "validate_power_connection",
    "validate_voltage_limits",
    "validate_io_voltage_compatibility",
    "validate_common_ground",
    "validate_power_paths",
    # Communication validators
    "GPIOConnectionValidator",
    "I2CConnectionValidator",
    "I2CAddressUniquenessValidator",
    "SPIConnectionValidator",
    "UARTConnectionValidator",
    "PWMConnectionValidator",
    "validate_gpio_connection",
    "validate_i2c_connection",
    "validate_i2c_address_uniqueness",
    "validate_spi_connection",
    "validate_uart_connection",
    "validate_pwm_connection",
    # Peripheral validators
    "PeripheralConnectivityValidator",
    "EssentialPinsValidator",
    "UniquePeripheralNamesValidator",
    "validate_all_peripherals_connected",
    "validate_essential_pins_connected",
    "validate_unique_peripheral_names",
    # Board validators
    "SingleBoardValidator",
    "PinConflictsValidator",
    "UniquePinNumbersValidator",
    "BoardPortsValidator",
    "validate_single_board",
    "validate_no_pin_conflicts",
    "validate_unique_pin_numbers",
    "validate_board_ports",
    # Device validators
    "BrokerRequirementsValidator",
    "NetworkRequirementsValidator",
    "BrokerSecurityValidator",
    "TopicFormatValidator",
    "validate_broker_requirements",
    "validate_network_requirements",
    "validate_broker_security",
    "validate_topic_format",
    "validate_mqtt_topic",
    "validate_amqp_topic",
    "validate_redis_topic",
    # General validators
    "DependencySourcesValidator",
    "ConnectionsOrchestratorValidator",
    "validate_dependency_sources",
    "validate_connections",
    # SmartConnect validators
    "SmartConnectValidator",
    "validate_smart_connections",
]
