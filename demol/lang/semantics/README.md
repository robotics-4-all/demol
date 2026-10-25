# Semantics Module - Validation Framework

This directory contains the refactored validation framework for DeMoL, organized into logical categories for better maintainability and extensibility.

## Directory Structure

```
semantics/
├── __init__.py               # Public API exports (backward compatibility)
├── core.py                   # Core validation infrastructure
├── utils.py                  # Helper functions
├── validators/
│   ├── __init__.py
│   ├── base.py               # BaseValidator abstract class
│   ├── alert.py              # ALERT trigger validation
│   ├── board.py              # Board-level validators
│   ├── communication.py      # GPIO, I2C, SPI, UART, PWM validators
│   ├── device.py             # Device-level validators (broker, network)
│   ├── general.py            # General/cross-cutting validators
│   ├── multi_broker.py       # Multi-broker VIA routing validation
│   ├── peripheral.py         # Peripheral connectivity validators
│   ├── peripheral_properties.py  # Peripheral property validation
│   ├── pin_oversubscription.py   # Pin function oversubscription warnings
│   ├── power.py              # Power connection validators
│   ├── power_budget.py       # Power budget analysis
│   ├── protocol_frequency.py # Bus speed constraint validation
│   ├── sampling.py           # SAMPLING block validation
│   ├── smart_connection.py   # SMARTCONNECT resolution validation
│   └── user_constraints.py   # CONSTRAINT expression validation
└── README.md                 # This file
```

## Module Responsibilities

### `core.py` - Validation Infrastructure
Manages validation state and error/warning collection:
- `clear_validation_results()` - Reset validation state
- `get_validation_errors()` - Retrieve collected errors
- `get_validation_warnings()` - Retrieve collected warnings
- `get_passed_rules()` - Retrieve passed validation rules
- `report_passed_rule()` - Record a passed validation
- `raise_validation_error()` - Collect an error
- `raise_validation_warning()` - Collect a warning
- `check_validation_errors()` - Check and raise if errors exist
- `ValidationError` - Custom exception class

### `utils.py` - Helper Functions
Shared utility functions used across validators:
- `get_connection_target()` - Extract target from connection
- `get_connection_endpoints()` - Get both connection endpoints
- `get_pin_functions()` - Extract pin functionality
- `parse_voltage()` - Parse voltage from string
- `are_voltages_compatible()` - Check voltage compatibility

### `validators/base.py` - Base Validator Class
Abstract base class that all validators inherit from:
- `BaseValidator.validate()` - Abstract validation method
- `BaseValidator.get_name()` - Return validator name
- `BaseValidator.get_description()` - Return validator description

### `validators/power.py` - Power Validators
Validates power connections and voltage compatibility:
- Power connection validation
- Voltage limits checking
- IO voltage compatibility
- Common ground validation
- Power path validation

### `validators/communication.py` - Communication Validators
Validates data connection protocols:
- GPIO connection validation
- I2C connection validation (with address uniqueness)
- SPI connection validation
- UART connection validation
- PWM connection validation
- Connection orchestration

### `validators/peripheral.py` - Peripheral Validators
Validates peripheral-specific rules:
- Peripheral connectivity (all peripherals connected)
- Essential pins connected
- Unique peripheral names

### `validators/board.py` - Board Validators
Validates board-specific rules:
- Single board requirement
- Pin conflicts detection
- Unique pin numbers
- Board ports validation

### `validators/device.py` - Device Validators
Validates device-level configuration:
- Broker requirements
- Network requirements
- Broker security
- Topic format validation (MQTT, AMQP, Redis)

### `validators/general.py` - General Validators
Cross-cutting validation concerns:
- Dependency sources validation
- Other general validations

### `validators/power_budget.py` - Power Budget Validators
Validates power budget against declared power sources:
- Power budget vs POWERSOURCE capacity
- Battery runtime estimation
- Power constraints validation

### `validators/sampling.py` - Sampling Validators
Validates SAMPLING block configuration:
- Sampling rate validation
- Sampling mode validation (continuous, on_change, batch, on_demand)
- Buffer configuration validation

### `validators/alert.py` - Alert Validators
Validates ALERT trigger configuration:
- Threshold condition validation
- PUBLISH target validation
- COOLDOWN period validation
- Per-OS capability validation

### `validators/user_constraints.py` - User Constraint Validators
Validates CONSTRAINT expression blocks:
- `count()` function validation
- `sum_power()` function validation
- Arithmetic expression validation
- Cross-entity constraint checking

### `validators/multi_broker.py` - Multi-Broker Validators
Validates multi-broker VIA routing:
- Broker reference validation
- VIA routing consistency
- Per-OS multi-broker capability

### `validators/smart_connection.py` - SmartConnect Validators
Validates SMARTCONNECT declarations:
- Automatic pin assignment validation
- Connectivity resolution

### `validators/pin_oversubscription.py` - Pin Oversubscription Validators
Warns about pin function overuse:
- Pin function oversubscription detection
- Usage warnings for shared pins

### `validators/protocol_frequency.py` - Protocol Frequency Validators
Validates bus speed and frequency constraints:
- Bus speed constraint validation
- Protocol frequency compatibility

### `validators/peripheral_properties.py` - Peripheral Property Validators
Validates peripheral hardware properties:
- Property completeness checking
- Hardware property constraints

## Adding a New Validator

### Step 1: Choose the Right Module
Determine which category your validator belongs to:
- **Power-related?** → `validators/power.py`
- **Power budget/runtime?** → `validators/power_budget.py`
- **Communication protocol?** → `validators/communication.py`
- **Protocol frequency/speed?** → `validators/protocol_frequency.py`
- **Peripheral-specific?** → `validators/peripheral.py`
- **Peripheral property completeness?** → `validators/peripheral_properties.py`
- **Board-specific?** → `validators/board.py`
- **Pin oversubscription warnings?** → `validators/pin_oversubscription.py`
- **Device/network/broker?** → `validators/device.py`
- **Multi-broker VIA routing?** → `validators/multi_broker.py`
- **SAMPLING block?** → `validators/sampling.py`
- **CONSTRAINT expression?** → `validators/user_constraints.py`
- **ALERT trigger?** → `validators/alert.py`
- **SMARTCONNECT resolution?** → `validators/smart_connection.py`
- **General/cross-cutting?** → `validators/general.py`

### Step 2: Create Your Validator Class

```python
from ..core import raise_validation_error
from .base import BaseValidator

class MyNewValidator(BaseValidator):
    """Validates my specific condition."""
    
    @staticmethod
    def get_name() -> str:
        return "My Validation Rule"
    
    @staticmethod
    def get_description() -> str:
        return "Checks that my specific condition is met"
    
    @staticmethod
    def validate(model, **kwargs):
        # Your validation logic here
        for item in model.items:
            if not item.is_valid:
                raise_validation_error(
                    item,
                    f"Item {item.name} is invalid",
                    "MyValidationError"
                )
```

### Step 3: Export Your Validator
Add your validator to the module's `__all__` list and to `validators/__init__.py`.

### Step 4: Use Your Validator
In `device.py`, call your validator:

```python
from demol.lang.semantics.validators.mymodule import MyNewValidator

# In model_proc():
run_rule("My Rule", MyNewValidator.validate, model, desc="My description")
```

## Backward Compatibility

The `__init__.py` file re-exports all functions to maintain backward compatibility with existing code:

```python
# Old code still works:
from demol.lang.semantics import validate_power_connection

# New code can use:
from demol.lang.semantics.validators.power import PowerConnectionValidator
```

## Testing

Each validator module has corresponding tests in `tests/` named with the `test_<category>_semantics` convention:
- `test_power_semantics` — power and board validators
- `test_i2c_spi_semantics` — communication validators
- `test_user_constraint_semantics` — CONSTRAINT expressions
- `test_alert_semantics` — ALERT triggers
- `test_sampling_semantics` — SAMPLING blocks
- `test_smart_connections` — SMARTCONNECT resolution
- `test_power_budget_semantics` — power budget analysis
- `test_protocol_frequency_semantics` — protocol frequency
- `test_general_semantics` — general validators

## Benefits of This Structure

1. **Easier Navigation**: Find validators by category
2. **Easier Extension**: Clear pattern for adding new validators
3. **Better Testing**: Test validators independently
4. **Better Documentation**: Focused documentation per category
5. **Reduced Coupling**: Validators are more independent
6. **Maintainability**: Smaller files are easier to understand

## Migration Complete

Migration complete: the legacy monolith was deleted in commit `ebc85bbe`; all 33 validator
classes now live in `demol/lang/semantics/validators/` across 15 files. The `__init__.py`
package re-exports all public symbols for backward compatibility.

### Per-Validator Index

| Validator Class | File | Purpose | OS-Keyed |
|-----------------|------|---------|:--------:|
| `AlertValidator` | `alert.py` | ALERT trigger conditions, PUBLISH, COOLDOWN | Y |
| `SingleBoardValidator` | `board.py` | Single board requirement | N |
| `PinConflictsValidator` | `board.py` | Pin conflict detection | N |
| `UniquePinNumbersValidator` | `board.py` | Unique pin numbers | N |
| `BoardPortsValidator` | `board.py` | Board ports validation | N |
| `GPIOConnectionValidator` | `communication.py` | GPIO connection validation | N |
| `I2CConnectionValidator` | `communication.py` | I2C connection validation | N |
| `I2CAddressUniquenessValidator` | `communication.py` | I2C address uniqueness (0x00-0x7F) | N |
| `SPIConnectionValidator` | `communication.py` | SPI connection validation | N |
| `UARTConnectionValidator` | `communication.py` | UART connection validation | N |
| `PWMConnectionValidator` | `communication.py` | PWM connection validation | N |
| `BrokerRequirementsValidator` | `device.py` | Broker declaration requirements | N |
| `NetworkRequirementsValidator` | `device.py` | Network declaration requirements | N |
| `BrokerSecurityValidator` | `device.py` | Broker security configuration | N |
| `TopicFormatValidator` | `device.py` | Topic format (MQTT, AMQP, Redis) | N |
| `DependencySourcesValidator` | `general.py` | Dependency sources validation | N |
| `ConnectionsOrchestratorValidator` | `general.py` | Connection orchestration | N |
| `MultiBrokerValidator` | `multi_broker.py` | Multi-broker VIA routing | Y |
| `PeripheralPropertyValidator` | `peripheral_properties.py` | Peripheral hardware properties | N |
| `PeripheralConnectivityValidator` | `peripheral.py` | All peripherals connected | N |
| `EssentialPinsValidator` | `peripheral.py` | Essential pins connected | N |
| `UniquePeripheralNamesValidator` | `peripheral.py` | Unique peripheral names | N |
| `PinOversubscriptionValidator` | `pin_oversubscription.py` | Pin function oversubscription warnings | N |
| `PowerConnectionValidator` | `power.py` | Power connection validation | N |
| `VoltageLimitsValidator` | `power.py` | Voltage limits checking | N |
| `IOVoltageCompatibilityValidator` | `power.py` | IO voltage compatibility (0.5V tolerance) | N |
| `CommonGroundValidator` | `power.py` | Common ground validation | N |
| `PowerPathValidator` | `power.py` | Power path validation | N |
| `PowerBudgetValidator` | `power_budget.py` | Power budget vs POWERSOURCE, battery runtime | N |
| `ProtocolFrequencyValidator` | `protocol_frequency.py` | Bus speed constraint validation | N |
| `SamplingValidator` | `sampling.py` | SAMPLING rate, mode, buffering | N |
| `SmartConnectValidator` | `smart_connection.py` | SMARTCONNECT resolution validation | N |
| `UserConstraintValidator` | `user_constraints.py` | CONSTRAINT count(), sum_power(), arithmetic | N |
