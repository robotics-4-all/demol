# Semantics Module - Validation Framework

This directory contains the refactored validation framework for DeMoL, organized into logical categories for better maintainability and extensibility.

## Directory Structure

```
semantics/
├── __init__.py              # Public API exports (maintains backward compatibility)
├── core.py                  # Core validation infrastructure
├── utils.py                 # Helper functions
├── validators/
│   ├── __init__.py
│   ├── base.py              # Base validator class
│   ├── power.py             # Power connection validators
│   ├── communication.py     # I2C, SPI, UART, PWM, GPIO validators
│   ├── peripheral.py        # Peripheral-specific validators
│   ├── board.py             # Board-specific validators
│   ├── device.py            # Device-level validators (network, broker)
│   └── general.py           # General/cross-cutting validators
└── README.md                # This file
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

## Adding a New Validator

### Step 1: Choose the Right Module
Determine which category your validator belongs to:
- **Power-related?** → `validators/power.py`
- **Communication protocol?** → `validators/communication.py`
- **Peripheral-specific?** → `validators/peripheral.py`
- **Board-specific?** → `validators/board.py`
- **Device/network/broker?** → `validators/device.py`
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

Each validator module should have corresponding tests in `tests/`:
- `test_power_semantics.py` → tests for `validators/power.py`
- `test_i2c_spi_semantics.py` → tests for communication validators
- etc.

## Benefits of This Structure

1. **Easier Navigation**: Find validators by category
2. **Easier Extension**: Clear pattern for adding new validators
3. **Better Testing**: Test validators independently
4. **Better Documentation**: Focused documentation per category
5. **Reduced Coupling**: Validators are more independent
6. **Maintainability**: Smaller files are easier to understand

## Migration Status

This is a work in progress. The refactoring is being done incrementally to maintain stability.

### Completed:
- ✅ Directory structure created
- ✅ `core.py` - Validation infrastructure
- ✅ `utils.py` - Helper functions
- ✅ `validators/base.py` - Base validator class
- ✅ README documentation

### In Progress:
- ⏳ Migrating validators from old `semantics.py`
- ⏳ Creating validator classes
- ⏳ Updating imports in `device.py`

### TODO:
- ⬜ Complete all validator migrations
- ⬜ Update `__init__.py` with all exports
- ⬜ Run full test suite
- ⬜ Update documentation
