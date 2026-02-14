# tests/ — Test Suite

## OVERVIEW

pytest suite: 19 test files covering semantic validation (12 files) and code generation transformations (7 files).

## STRUCTURE

```
tests/
├── conftest.py                     # Fixtures: device_mm, component_mm (session-scoped)
├── models/
│   ├── valid/                      # 4 valid .dev models for integration tests
│   └── invalid/                    # 4 invalid .dev models for error detection tests
├── test_board_semantics.py         # Board: port counts, pin uniqueness
├── test_component_semantics.py     # Sensor/Actuator: attributes, templates
├── test_device_semantics.py        # Device-level: IO voltage, GND, topics
├── test_power_gpio_semantics.py    # Power voltage compat, GPIO modes
├── test_power_semantics.py         # Comprehensive power connection validation
├── test_i2c_spi_semantics.py       # I2C address range/uniqueness, SPI
├── test_uart_safety_semantics.py   # UART baudrates, pin conflicts, connectivity
├── test_pwm_semantics.py           # PWM connection validation
├── test_pin_conflicts.py           # Pin reuse detection
├── test_missing_pin_validation.py  # Essential pin requirements
├── test_network_semantics.py       # Network configuration
├── test_power_path_bug.py          # Regression: power path issues
├── test_rpi_transformation.py      # RPi Python code generation
├── test_riot_transformation.py     # RiotOS C code generation
├── test_smauto_transformation.py   # SmartAuto M2M transformation
├── test_docs_transformation.py     # Markdown docs generation
├── test_svg_transformation.py      # SVG diagram generation
└── test_json_demol.py              # JSON serialization roundtrip
```

## CONVENTIONS

- **Naming**: `test_<domain>_<aspect>.py` (e.g., `test_power_gpio_semantics.py`)
- **Fixtures**: Use `device_mm` for device model tests, `component_mm` for `.hwd` tests — both session-scoped
- **Validation errors**: `with pytest.raises(TextXSemanticError, match="pattern")`
- **Validation warnings**: `with pytest.warns(UserWarning, match="pattern")`
- **Inline models**: Tests define DSL strings inline — no external file dependencies (except `models/` dir for integration tests)
- **Test output**: Generated files go to `tests/output/` (gitignored)

## WRITING A TEST

```python
def test_invalid_voltage(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="test", author="test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680(Sensor1);
    CONNECT Sensor1 WITH
        POWER gnd_1 -- gnd, power_3v3 -- vcc  // 3.3V to 5V pin = error
        DATA i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl;
    """
    with pytest.raises(TextXSemanticError, match="Incompatible power"):
        device_mm.model_from_str(model_str)
```

## ANTI-PATTERNS

- Do NOT create external `.dev` files for unit tests — use inline strings for isolation
- Do NOT skip `clear_validation_state` fixture — it auto-runs via conftest.py
- Tests for new validators should go in the appropriate `test_<category>_semantics.py` file
- Transformation tests should verify file existence AND content, not just no-exception
