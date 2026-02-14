# demol/lang/semantics/ — Validator Framework

## OVERVIEW

Modular semantic validation framework. Migrating from `../semantics.py` monolith (1776 lines) into category-based validator classes.

## STRUCTURE

```
semantics/
├── __init__.py      # Public API re-exports (backward compat with monolith)
├── core.py          # Validation state: error/warning collection, ValidationError
├── utils.py         # Helpers: parse_voltage(), get_pin_functions(), are_voltages_compatible()
├── README.md        # Detailed framework documentation
└── validators/
    ├── base.py          # BaseValidator abstract class
    ├── power.py         # Power connections: voltage compat, GND rules, power path (412 lines)
    ├── communication.py # GPIO, I2C, SPI, UART, PWM validation (637 lines)
    ├── peripheral.py    # Peripheral connectivity, essential pins, unique names (182 lines)
    ├── board.py         # Single board, pin conflicts, unique pin numbers, ports (317 lines)
    ├── device.py        # Broker requirements, network, topic format, IO voltage (350 lines)
    └── general.py       # Cross-cutting: dependency sources, well-formedness (329 lines)
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add power validation | `validators/power.py` | Voltage compat (0.5V tolerance), GND, power path |
| Add protocol validation | `validators/communication.py` | I2C addr (0x00-0x7F), SPI modes (0-3), UART baudrates |
| Add peripheral rule | `validators/peripheral.py` | Connectivity, essential pins |
| Add board rule | `validators/board.py` | Pin conflicts, port counts |
| Add device-level rule | `validators/device.py` | Broker, network, topic format |
| Collect errors | `core.py` | `raise_validation_error(node, msg, rule_name)` |

## ADDING A VALIDATOR

```python
from ..core import raise_validation_error, report_passed_rule
from .base import BaseValidator

class MyValidator(BaseValidator):
    @staticmethod
    def get_name() -> str:
        return "My-Rule-Name"

    @staticmethod
    def get_description() -> str:
        return "Checks that X holds"

    @staticmethod
    def validate(model, **kwargs):
        for item in model.items:
            if not item.valid:
                raise_validation_error(item, f"...", "My-Rule-Name")
        report_passed_rule("My-Rule-Name")
```

Then register in `device.py`: `run_rule("My Rule", MyValidator.validate, model)`

## MIGRATION STATUS

- `../semantics.py` (monolith) still exists and is imported
- `__init__.py` re-exports monolith functions for backward compatibility
- New validators go here; old validators being migrated incrementally
- Both are active — do not delete the monolith until migration complete

## ANTI-PATTERNS

- **NEVER** add new validators to `../semantics.py` — always use this framework
- **NEVER** raise `TextXSemanticError` directly — use `raise_validation_error()` from `core.py`
- **NEVER** call `clear_validation_results()` except in test fixtures or at validation start
- Rule names must follow `[Category-Rule]` convention for consistent error output
