# tests/ — Test Suite

## OVERVIEW

pytest suite: 76 test files covering semantic validation, code generation (RPi, RIOT, Zephyr, Wokwi, Renode), CLI utilities, and advanced DSL features. The RPi codegen syntax gate parametrizes over **41+ examples** and runs both `ast.parse` and `py_compile` on every emitted Python file. ALERT codegen is covered by `test_rpi_alerts_emission.py` (string assertions on emitted Python), `test_alert_runtime.py` (importlib-loads the rendered `alerts.py` and exercises `AlertTrigger.evaluate` end-to-end), and `test_riot_alerts_emission.py` (string assertions on emitted C, including SCALE arithmetic and the `publish_alert` cooldown gate). Zephyr and RIOT driver codegen is covered by per-peripheral test files (e.g., `test_zephyr_bme280_codegen.py`, `test_riot_bme280_codegen.py`). CONSTRAINT runtime is covered by `test_riot_constraint_codegen.py`, `test_zephyr_constraint_codegen.py`, and `test_rpi_constraint_codegen.py`. AMQP/Redis broker support is covered by `test_rpi_amqp_redis_codegen.py`.

## STRUCTURE

```
tests/
├── conftest.py                     # Fixtures: device_mm, component_mm, device_mm_skip (session-scoped); clear_validation_state (function autouse)
├── models/
│   ├── valid/                      # Valid .dev models for integration tests
│   └── invalid/                    # Invalid .dev models for error detection tests
├── output/                         # Generated test output (gitignored)
│
│ # Semantic Validation (14 files)
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
├── test_meta_os_not_supported.py   # [Meta-OS-NotSupported] validator
├── test_alert_validator_per_os.py  # Per-OS alert capability validation
│
│ # Code Generation (37 files)
├── test_rpi_transformation.py      # RPi Python code generation (file-existence + substring assertions)
├── test_rpi_codegen_syntax.py      # ast.parse + py_compile over generated Python for every examples/rpi/*.dev
├── test_rpi_alerts_emission.py     # ALERT emission for RPi: alerts.py runtime, AlertTrigger imports, broker routing
├── test_alert_runtime.py           # Importlib-loads emitted alerts.py and exercises AlertTrigger.evaluate
├── test_rpi_template_rendering.py  # RPi template rendering tests
├── test_rpi_constraint_codegen.py  # CONSTRAINT runtime codegen for RPi (constraints.py)
├── test_rpi_amqp_redis_codegen.py  # AMQP/Redis broker codegen for RPi
├── test_riot_transformation.py     # RiotOS C code generation
├── test_riot_alerts_emission.py    # ALERT emission for RIOT: publish_alert wrapper, SCALE arithmetic
├── test_riot_constraint_codegen.py # CONSTRAINT runtime codegen for RIOT (constraint.c/h)
├── test_riot_bme280_codegen.py     # RIOT BME280 driver codegen
├── test_riot_bh1750_codegen.py     # RIOT BH1750 driver codegen
├── test_riot_pir_hcsr501_codegen.py # RIOT PIR_HCSR501 driver codegen
├── test_riot_relay_codegen.py      # RIOT relay driver codegen
├── test_riot_dht22_codegen.py      # RIOT DHT22 driver codegen
├── test_riot_ds18b20_codegen.py    # RIOT DS18B20 driver codegen
├── test_zephyr_codegen.py          # Zephyr C code generation
├── test_zephyr_alert_codegen.py    # ALERT emission for Zephyr
├── test_zephyr_sampling_codegen.py # SAMPLING block codegen for Zephyr
├── test_zephyr_mqtt_codegen.py     # MQTT broker codegen for Zephyr
├── test_zephyr_constraint_codegen.py # CONSTRAINT runtime codegen for Zephyr (constraint.c/h)
├── test_zephyr_bme280_codegen.py   # Zephyr BME280 driver codegen
├── test_zephyr_bh1750_codegen.py   # Zephyr BH1750 driver codegen
├── test_zephyr_pir_hcsr501_codegen.py # Zephyr PIR_HCSR501 driver codegen
├── test_zephyr_dht22_codegen.py    # Zephyr DHT22 driver codegen
├── test_zephyr_ds18b20_codegen.py  # Zephyr DS18B20 driver codegen
├── test_zephyr_goldens.py          # Zephyr golden-file snapshot tests
├── test_wokwi_codegen.py           # Wokwi diagram.json generation
├── test_wokwi_goldens.py           # Wokwi golden-file snapshot tests
├── test_renode_codegen.py          # Renode .repl + pyrenode3 generation
├── test_renode_goldens.py          # Renode golden-file snapshot tests
├── test_renode_runtime.py          # Renode runtime validation
├── test_smauto_transformation.py   # SmartAuto M2M transformation
├── test_docs_transformation.py     # Markdown docs generation
├── test_svg_transformation.py      # SVG diagram generation
├── test_json_demol.py              # JSON serialization roundtrip
├── test_pinmap_transformation.py   # Pinmap report generation
│
│ # Advanced DSL Features (9 files)
├── test_user_constraints.py        # CONSTRAINT expressions: count(), sum_power()
├── test_alert.py                   # ALERT triggers with conditions, PUBLISH, COOLDOWN
├── test_sampling.py                # SAMPLING blocks: rate, mode, on_change
├── test_smart_connection.py        # SMARTCONNECT auto pin resolution
├── test_multi_broker.py            # Multi-broker VIA routing
├── test_power_budget.py            # Power budget analysis, battery runtime
├── test_protocol_frequency.py      # Protocol bus frequency constraints
├── test_pin_oversubscription.py    # Pin function overuse warnings
├── test_performance.py             # Parse/validate timing regression thresholds
│
│ # CLI & Parser (3 files)
├── test_autofix.py                 # Auto-fix common validation errors
├── test_modeldiff.py               # Semantic model diff
├── test_parser_robustness.py       # Malformed input, boundary values, encoding
│
│ # Infrastructure (13 files)
├── test_base_generator.py          # BaseCodeGenerator unit tests
├── test_board_registry.py          # BoardNameRegistry resolution tests
├── test_docker_mixin.py            # DockerBuildMixin tests
├── test_template_mapper.py         # PeripheralTemplateMapper tests
├── test_pin_pool.py                # Pin pool allocation tests
├── test_power_budget_and_smart_connection_helpers.py # Helper method tests
├── test_validation_reporter.py     # ValidationReporter output tests
├── test_cli_runner.py              # CLI integration tests
├── test_cross_backend_integration.py # Cross-backend round-trip tests
├── test_wave4_peripherals.py       # Wave 4 peripheral porting validation
├── test_golden_completeness.py     # Golden-file completeness check
├── test_examples_parsing.py        # All examples parse without errors
└── test_semantics_doc_paths.py     # Semantics doc path validation
```

## CONVENTIONS

- **Naming**: `test_<domain>_<aspect>.py` (e.g., `test_power_gpio_semantics.py`)
- **Fixtures**: Use `device_mm` for device model tests, `component_mm` for `.hwd` tests — both session-scoped
- **Validation errors**: `with pytest.raises(TextXSemanticError, match="pattern")`
- **Validation warnings**: `with pytest.warns(UserWarning, match="pattern")`
- **Inline models**: Tests define DSL strings inline — no external file dependencies (except `models/` dir for integration tests)
- **Test output**: Generated files go to `tests/output/` (gitignored)
- **Golden files**: Zephyr, Wokwi, and Renode backends use syrupy snapshot testing in `tests/goldens/{zephyr,wokwi,renode}/`
- **Cross-backend**: `test_cross_backend_integration.py` round-trips a model through all applicable backends
- **Per-driver codegen**: RIOT and Zephyr each have per-peripheral test files (e.g., `test_riot_bme280_codegen.py`, `test_zephyr_bme280_codegen.py`) that verify emitted C code structure

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
