# demol/lang/semantics/validators/ — Validator Classes

## OVERVIEW

15 validator files implementing `BaseValidator`. Each handles one validation domain. All registered in `demol/lang/device.py` via `run_rule()`. See `../README.md` for the framework guide.

## VALIDATOR INVENTORY

| File | Classes / Purpose | Lines |
|------|-------------------|-------|
| `base.py` | `BaseValidator` abstract: `validate(model, **kwargs)`, `get_name()`, `get_description()` | 77 |
| `power.py` | `PowerConnectionValidator` (voltage compat, GND/VCC mix), `VoltageLimitsValidator`, `IOVoltageCompatibilityValidator`, `CommonGroundValidator`, `PowerPathValidator` | 421 |
| `communication.py` | `GPIOValidator`, `I2CValidator` (addr 0x00-0x7F, bus speed, uniqueness), `SPIValidator` (mode 0-3), `UARTValidator` (baudrate, parity, stop bits), `PWMValidator`, `ConnectionOrchestrator` | 633 |
| `board.py` | `SingleBoardValidator`, `PinConflictsValidator` (shared I2C/power pins OK), `UniquePinNumbersValidator`, `BoardPortsValidator` | 311 |
| `peripheral.py` | `PeripheralConnectivityValidator`, `EssentialPinsValidator`, `UniquePeripheralNamesValidator` | 181 |
| `device.py` | `BrokerRequirementsValidator`, `NetworkRequirementsValidator`, `BrokerSecurityValidator` (warns remote+no-auth), `TopicFormatValidator` (MQTT/AMQP/Redis patterns) | 355 |
| `general.py` | `DependencySourcesValidator` (pip/apt only), cross-cutting well-formedness | 330 |
| `power_budget.py` | `PowerBudgetValidator` — evaluates `sum_power(PERIPHERAL)` vs POWERSOURCE capacity, battery runtime estimation | 336 |
| `user_constraints.py` | `UserConstraintsValidator` — evaluates `CONSTRAINT` expressions: `count()`, `sum_power()`, arithmetic, aggregates, custom MESSAGE strings | 422 |
| `alert.py` | `AlertValidator` — validates `ALERT` triggers: threshold expressions, `&&` conditions, `PUBLISH ... VIA`, `COOLDOWN` | 209 |
| `sampling.py` | `SamplingValidator` — rate (Hz), mode (`continuous`, `on_change`, `batch`), threshold, buffer_size | 125 |
| `smart_connection.py` | `SmartConnectionValidator` — validates SMARTCONNECT auto-wiring results after resolution | 78 |
| `multi_broker.py` | Validates `VIA BrokerName` references — broker must be declared in model | — |
| `pin_oversubscription.py` | `PinOversubscriptionValidator` — warns when I2C/SPI pin is also used as GPIO | 139 |
| `protocol_frequency.py` | `ProtocolFrequencyValidator` — I2C/SPI bus speed constraints per board spec | 171 |

## ADDING A VALIDATOR

```python
from ..core import raise_validation_error, report_passed_rule
from .base import BaseValidator

class MyValidator(BaseValidator):
    @staticmethod
    def get_name() -> str:
        return "[My-Rule-Name]"          # [Category-Rule] convention

    @staticmethod
    def get_description() -> str:
        return "Checks that X holds"

    @staticmethod
    def validate(model, **kwargs):
        for item in model.items:
            if not item.valid:
                raise_validation_error(item, f"Item {item.name} is invalid", "[My-Rule-Name]")
        report_passed_rule("[My-Rule-Name]")   # Always call on success
```

Register in `demol/lang/device.py`: `run_rule("My Rule", MyValidator.validate, model)`

## ANTI-PATTERNS

- Never import from `../../semantics.py` monolith in new validators
- Never raise `TextXSemanticError` directly — always use `raise_validation_error()` from `..core`
- Rule name strings must follow `[Category-Rule]` format
- Always call `report_passed_rule()` at end of a fully successful validation pass
- Never call `clear_validation_results()` from within a validator (only test fixtures)
