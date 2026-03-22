# demol/grammar/ — textX Grammar Files

## OVERVIEW

4 textX grammar files defining the complete DeMoL DSL syntax. `common.tx` is imported by the other three.

## FILES

| File | Grammar Rules | Role |
|------|--------------|------|
| `device.tx` | `DeviceModel`, `Device`, `Network`, `WiFiNetwork`, `EthNetwork`, `Connect`, `SmartConnect`, `Sampling`, `Constraint`, `Alert`, `PowerConn`, `DataConn` | Top-level `.dev` file grammar (main entry point) |
| `component.tx` | `ComponentModel`, `Component`, `Board`, `BoardType`, `Sensor`, `Actuator`, `PowerSource`, `Port`, `Pin`, `PinFunction` | Hardware component grammar for `.hwd` files |
| `communication.tx` | `MessageBroker`, `MQTTBroker`, `AMQPBroker`, `RedisBroker` | Broker configuration grammar |
| `common.tx` | `FQN`, `Import`, `AttributeSet`, `Attribute` subtypes, units (`FrequencyUnit`, `PowerUnit`, etc.), `IP_ADDR` | Shared types imported by all other files |

## CONVENTIONS

- textX assignment operators: `=` (single), `*=` (zero-or-more list), `?=` (boolean flag), `+=` (one-or-more)
- `common.tx` must be imported at the top of files that use shared types
- Grammar rules map directly to Python classes in the textX metamodel (auto-generated)
- Grammar changes in `device.tx` affect all `.dev` model files — update validators accordingly
- Grammar changes in `component.tx` affect all `.hwd` hardware definition files

## KEY SYNTAX PATTERNS

```
# Board/peripheral pin definition (component.tx)
PinName[func1,func2] @ number

# Manual connection block (device.tx)
CONNECT PeriphName WITH
    POWER gnd_pin -- gnd, vcc_pin -- vcc
    DATA i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl
    @ "topic/path"
    VIA BrokerName;

# Auto-wiring (device.tx)
SMARTCONNECT PeriphName @ "topic/path";

# Sampling (device.tx)
SAMPLING PeriphName WITH rate = 10 hz, mode = on_change, threshold = 0.1;

# Constraint (device.tx)
CONSTRAINT budget: sum_power(PERIPHERAL) < 5 W MESSAGE "Budget exceeded";

# Alert (device.tx)
ALERT frost ON Sensor WHEN temperature < 2 THEN PUBLISH "alerts/frost" VIA Cloud COOLDOWN 60 hz;
```

## ANTI-PATTERNS

- Grammar changes require updating validators in `lang/semantics/validators/` — never change grammar alone
- Do NOT add new DSL keywords without also updating `device.tx` semantics and test coverage
- `common.tx` changes cascade to all other grammar files — change with care
- Template file names in component `.hwd` files must match actual files in `templates/` directory
