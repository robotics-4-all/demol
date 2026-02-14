# Semantic Validation

DeMoL implements comprehensive semantic validations based on the [formal semantics specification](semantics.md). These validations ensure device models are well-formed, safe, and correct before code generation.

## Validation Categories

### Power Connection Validation

Ensures electrical compatibility between board and peripheral power connections:

- **Voltage Compatibility**: Power pins must have compatible voltages (within 0.5V tolerance)
- **GND Connections**: Both pins must be GND when connecting ground
- **VCC Connections**: Non-GND voltages must match peripheral requirements
- **Voltage Limits**: Power supplied must not exceed peripheral's maximum rated voltage

**Example Error:**
```
[Conn-Power] Incompatible power connection: board pin power_5v (5.0V) cannot 
connect to peripheral pin vcc (3.3V). Voltage difference exceeds 0.5V tolerance.
```

### IO Connection Validation

Validates pin functionality and protocol-specific requirements:

**GPIO Connections:**
- Both pins must have GPIO functionality
- Valid properties: `mode` (input/output), `pullup`, `pulldown`
- Mode must be either 'input' or 'output'

**I2C Connections:**
- Board and peripheral pins must have SDA/SCL functionality
- Slave address must be in range 0x00-0x7F
- Valid properties: `slave_address`, `bus_speed`
- All I2C addresses on the same bus must be unique

**SPI Connections:**
- All required pins (MOSI, MISO, SCK, CS) must have SPI functionality
- Valid properties: `bus_speed`, `mode` (0-3)

**UART Connections:**
- TX/RX pins must have proper UART functionality
- Board TX connects to Peripheral RX (and vice versa)
- Baudrate must be a common value (9600, 115200, etc.)
- Valid properties: `baudrate`, `parity`, `stop_bits`, `data_bits`

**Example Errors:**
```
[Conn-GPIO] Board pin GPIO5 does not have GPIO functionality.

[Conn-I2C] I2C slave address 0x80 out of valid range [0x00-0x7F]

[Conn-UART] Board pin TX connects to Peripheral TX. UART requires 
connecting Board TX to Peripheral RX.
```

### Safety Properties

Critical safety validations to prevent hardware damage:

**Pin Conflict Detection:**
- Each board pin can only be used once (except I2C and power pins)
- I2C pins (SDA/SCL) can be shared (bus architecture)
- Power pins (GND/VCC) can be shared (common nets)

**IO Voltage Compatibility:**
- Board IO voltage must match peripheral IO voltage
- Prevents communication errors and potential damage
- Emits warnings for voltage mismatches

**Common Ground Validation:**
- Each peripheral should have at least one GND connection
- Ensures proper electrical reference and signal integrity
- Emits warnings when ground connection is missing

**Example Errors:**
```
[Safety-Pin-Conflicts] Pin conflict detected: Board pin 'GPIO4' is already 
used by peripheral 'Sensor1' as 'GPIO'. Cannot reuse for peripheral 'Sensor2'.

[Safety-I2C-Address] I2C address conflict: Address 0x76 is already used by 
peripheral(s): BME680. Cannot reuse for peripheral 'TempSensor'.

[Safety-IO-Voltage] IO Voltage Incompatibility: Board 'RaspberryPi_5_8GB' 
operates at 5.0V (IO), but peripheral 'BME680' operates at 3.3V (IO).
```

### Well-Formedness Rules

Structural validations ensuring model completeness:

- **All Peripherals Connected**: Every peripheral must have at least one connection
- **Unique Peripheral Names**: All peripheral instances must have unique names
- **Unique Pin Numbers**: Pin numbers must be unique within each component
- **Broker Requirements**: Broker must be configured if remote endpoints are used
- **Pin Existence**: All referenced pins must exist in component definitions

**Example Errors:**
```
[WF-All-Peripherals-Connected] Unconnected peripherals detected: DistanceSensor. 
All peripherals must have at least one connection defined.

[WF-Unique-Peripheral-Names] Duplicate peripheral name 'MySensor'. Peripheral 
names must be unique within the device.

[WF-Unique-Pin-Numbers] Duplicate pin number 4 used by pins: GPIO4, SDA1. Pin 
numbers must be unique within a component.
```

## Validation Workflow

1. **Syntax Validation**: textX parser validates grammar compliance
2. **Semantic Validation**: Custom validators check:
   - Power connection compatibility
   - IO connection functionality
   - Safety properties (pin conflicts, voltage limits)
   - Well-formedness rules
3. **Warning Generation**: Non-critical issues emit warnings:
   - IO voltage incompatibility
   - Missing ground connections
   - Unusual baudrates

## Running Validations

**Validate a single model:**
```sh
demol validate examples/rpi_iot_device.dev
```

**Validate all examples:**
```sh
python scripts/validate_examples.py
```

**Validate builtin hardware models:**
```sh
python scripts/validate_builtin_models.py
```

## Skipping Semantic Validation

If you want to build or validate a model even if semantic rules are failing (e.g., for testing or partial code generation), use the `--skip-semantics` flag. This flag is supported by the `validate` command and all `generate` commands:

```sh
# Validate with errors ignored
demol validate examples/rpi/multi_periph.dev --skip-semantics

# Generate SVG even with semantic errors
demol generate svg examples/rpi/multi_periph.dev --skip-semantics
```

This will report all errors but return a success exit code, allowing the process to continue.

Otherwise, transformations will not proceed:

```sh
➜ demol generate docs examples/rpi/multi_periph.dev                 
[*] Generating documentation for model examples/rpi/multi_periph.dev
[*] Processing model: /home/klpanagi/Development/dsls/demol/examples/rpi/multi_periph.dev


Found 4 validation error(s):
  ✗ [Safety-IO-Voltage] Board 'RaspberryPi_5_8GB' operates at 3.3V (IO), but peripheral 'SRF05' operates at 5.0V (IO). This may cause communication errors or damage. (multi_periph.dev:34:1)
  ✗ [Safety-IO-Voltage] Board 'RaspberryPi_5_8GB' operates at 3.3V (IO), but peripheral 'WS2812' operates at 5.0V (IO). This may cause communication errors or damage. (multi_periph.dev:44:1)
  ✗ [Safety-IO-Voltage] Board 'RaspberryPi_5_8GB' operates at 3.3V (IO), but peripheral 'TCRT5000' operates at 5.0V (IO). This may cause communication errors or damage. (multi_periph.dev:53:1)
  ✗ [Safety-IO-Voltage] Board 'RaspberryPi_5_8GB' operates at 3.3V (IO), but peripheral 'TactileButton' operates at 5.0V (IO). This may cause communication errors or damage. (multi_periph.dev:62:1)

[!] Validation failed with 4 error(s).
```

## Validation Output

**Successful validation:**
```
[*] Processing model: examples/rpi_iot_device.dev
[✓] All validation checks passed!
```

**Validation with warnings:**
```
[*] Processing model: examples/esp_iot_device.dev
⚠ [Safety-IO-Voltage] IO Voltage Incompatibility at examples/esp_iot_device.dev:26
[✓] Validation passed with warnings
```

**Validation failure:**
```
[*] Processing model: examples/invalid_device.dev
✗ [Conn-Power] Incompatible power connection: board pin power_5v (5.0V) 
  cannot connect to peripheral pin vcc (3.3V)
```

## Implementation

All semantic validations are implemented in `demol/lang/semantics.py` based on the formal semantics specification. The validation system uses:

- **Type checking** for pin functionality verification
- **Constraint validation** for safety properties
- **Well-formedness rules** for structural correctness
- **Location tracking** for precise error reporting

For the complete formal specification of validation rules, see [semantics.md](semantics.md) sections 4 (Well-Formedness), 7 (Type System), and 8 (Verification Conditions).