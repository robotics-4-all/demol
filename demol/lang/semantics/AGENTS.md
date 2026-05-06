# demol/lang/semantics/ — Validator Framework

## OVERVIEW

Modular semantic validation framework: 21 validator classes across 14 category files. Migrating from `../semantics.py` monolith (1727 lines) into category-based validator classes. Both are active — do not delete monolith until migration complete.

## STRUCTURE

```
semantics/
├── __init__.py      # Public API re-exports (backward compat with monolith, 265 lines)
├── core.py          # Validation state: error/warning collection, ValidationError (81 lines)
├── utils.py         # Helpers: parse_voltage(), get_pin_functions(), are_voltages_compatible() (123 lines)
├── README.md        # Detailed framework documentation (195 lines)
└── validators/
    ├── base.py              # BaseValidator abstract class (77 lines)
    ├── power.py             # 5 classes: PowerConnection, VoltageLimits, IOVoltageCompatibility, CommonGround, PowerPath (428 lines)
    ├── communication.py     # 6 classes: GPIO, I2C, I2CAddressUniqueness, SPI, UART, PWM (634 lines)
    ├── peripheral.py        # 3 classes: PeripheralConnectivity, EssentialPins, UniquePeripheralNames (181 lines)
    ├── board.py             # 4 classes: SingleBoard, PinConflicts, UniquePinNumbers, BoardPorts (304 lines)
    ├── device.py            # 4 classes: BrokerRequirements, NetworkRequirements, BrokerSecurity, TopicFormat (355 lines)
    ├── general.py           # 2 classes: DependencySources, ConnectionsOrchestrator (330 lines)
    ├── power_budget.py      # PowerBudgetValidator: budget vs POWERSOURCE, battery runtime (340 lines)
    ├── user_constraints.py  # UserConstraintValidator: CONSTRAINT count(), sum_power(), arithmetic (422 lines)
    ├── alert.py             # AlertValidator: conditions, PUBLISH, COOLDOWN (209 lines)
    ├── sampling.py          # SamplingValidator: rate, mode, buffering (125 lines)
    ├── smart_connection.py  # SmartConnectValidator (78 lines)
    ├── multi_broker.py      # MultiBrokerValidator: VIA routing references (74 lines)
    ├── pin_oversubscription.py  # PinOversubscriptionValidator: function overuse warnings (139 lines)
    └── protocol_frequency.py   # ProtocolFrequencyValidator: bus speed constraints (171 lines)
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add power validation | `validators/power.py` | Voltage compat (0.5V tolerance), GND, power path |
| Add protocol validation | `validators/communication.py` | I2C addr (0x00-0x7F), SPI modes (0-3), UART baudrates |
| Add peripheral rule | `validators/peripheral.py` | Connectivity, essential pins |
| Add board rule | `validators/board.py` | Pin conflicts, port counts |
| Add device-level rule | `validators/device.py` | Broker, network, topic format |
| Add CONSTRAINT rule | `validators/user_constraints.py` | count(), sum_power(), arithmetic |
| Add ALERT rule | `validators/alert.py` | Threshold conditions, PUBLISH VIA, COOLDOWN |
| Add SAMPLING rule | `validators/sampling.py` | rate, mode, on_change threshold |
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

- `../semantics.py` (monolith, 1727 lines) still exists and is imported
- `__init__.py` (265 lines) re-exports monolith functions for backward compatibility
- All new feature validators (power_budget, user_constraints, alert, sampling, smart_connection, multi_broker, pin_oversubscription, protocol_frequency) are in this framework
- Protocol/power/board/peripheral validators are also migrated; monolith has legacy equivalents
- Both are active — do not delete the monolith until migration complete

## ANTI-PATTERNS

- **NEVER** add new validators to `../semantics.py` — always use this framework
- **NEVER** raise `TextXSemanticError` directly — use `raise_validation_error()` from `core.py`
- **NEVER** call `clear_validation_results()` except in test fixtures or at validation start
- Rule names must follow `[Category-Rule]` convention for consistent error output
