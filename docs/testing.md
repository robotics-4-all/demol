# Testing

## Running Tests

```bash
# Install test dependencies (if not already installed)
pip install pytest

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_board_semantics.py

# Run with coverage
make test-cov
```

## Test Structure

Test files are located in `tests/` with model fixtures in `tests/models/valid/` and `tests/models/invalid/`. The test suite uses session-scoped fixtures (`device_mm`, `component_mm`) defined in `tests/conftest.py` for metamodel reuse across tests.

**Total: 114 tests across 19 test files.**

## Test Coverage

### Semantic Validation Tests

- **test_board_semantics.py** — Board model semantics: port count consistency, nested operational properties, unique pin numbers.
- **test_component_semantics.py** — Component (Sensor/Actuator) semantics: valid definitions, attribute parsing, template parsing.
- **test_device_semantics.py** — Device model semantics: IO voltage compatibility, common ground connection, MQTT topic format, pin function compatibility.
- **test_power_gpio_semantics.py** — Power and GPIO connection semantics: voltage compatibility, ground connection rules, GPIO mode validation (input/output), GPIO property validation.
- **test_i2c_spi_semantics.py** — I2C and SPI connection semantics: I2C address range and uniqueness, bus speed validation, pin function checks (SDA/SCL).
- **test_uart_safety_semantics.py** — UART and safety semantics: baudrate validation, pin conflict detection, unique peripheral names, unconnected peripheral detection, broker requirement validation.
- **test_pin_conflicts.py** — Pin conflict detection: GPIO conflicts, I2C pin sharing, power pin sharing, mixed usage conflicts.
- **test_missing_pin_validation.py** — Missing pin validation: source/target pin existence, power pin existence on board and peripherals.
- **test_network_semantics.py** — Network and broker configuration: mandatory network/broker rules, missing network detection.
- **test_power_semantics.py** — Power path validation: board-to-peripheral power, direct power sources, chained power, missing power detection.
- **test_power_path_bug.py** — Power path edge cases: power bank connections, user model regression tests.
- **test_pwm_semantics.py** — PWM connection semantics: valid connections, channel validation, frequency/duty cycle bounds, pin conflicts with GPIO.

### SmartConnect Tests

- **test_smart_connection.py** — SmartConnect feature (20 tests): basic parsing, multiple peripherals, GPIO sensor/actuator resolution, I2C sharing and address conflicts, mixed manual+smart connections, pin avoidance, optional pin handling, duplicate/conflict detection, enrichment verification, deterministic allocation.

### Transformation Tests

- **test_rpi_transformation.py** — Raspberry Pi code generation: basic sensor/actuator output, dependency resolution, proximity sensors, ADC support.
- **test_riot_transformation.py** — RiotOS code generation: basic output, proximity sensors, WS2812 LED strips, HW006 peripherals.
- **test_docs_transformation.py** — Documentation generation: basic sensor/actuator hardware guides.
- **test_smauto_transformation.py** — SMAuto model generation: basic transformation, actuator output, frequency handling, broker variants.
- **test_json_demol.py** — JSON bidirectional conversion: basic structure, peripherals, connection logic, GPIO/UART connections.
