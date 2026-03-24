<div align="center">

![DeMoL](https://github.com/robotics-4-all/demol/blob/main/assets/demol_logo.png)

**A textX-based DSL for hardware-aware IoT device modeling with automated code generation, semantic validation, and visual design.**

[![CI](https://github.com/robotics-4-all/demol/actions/workflows/ci.yml/badge.svg)](https://github.com/robotics-4-all/demol/actions/workflows/ci.yml)
<img src="https://img.shields.io/badge/Python-3776AB.svg?style=default&logo=Python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/textX-2496ED.svg?style=default&logo=textx&logoColor=white" alt="textX">
<img src="https://img.shields.io/badge/Docker-2496ED.svg?style=default&logo=Docker&logoColor=white" alt="Docker">

</div>

---

## Overview

**DeMoL (Device Modeling Language)** is a domain-specific language for the automated synthesis of IoT device software in a hardware-aware manner. Define your hardware configuration, peripheral connections, and communication protocols declaratively — DeMoL generates platform-specific code (Python for Raspberry Pi, C for RiotOS) with rigorous semantic validation ensuring electrical safety and correctness.

![DeMoL Conceptual Model](assets/DeMoL_Conceptual.png)

## Features

|      |        Feature         | Summary |
| :--- | :--------------------: | :------ |
| 🔌 | **Hardware-Aware** | <ul><li>Explicit modeling of board specifications (pins, voltages, frequencies)</li><li>Peripheral component definitions (sensors, actuators)</li><li>Electrical compatibility checks (voltage levels, power constraints)</li></ul> |
| 🛡️ | **Semantic Safety** | <ul><li>Rigorous validation of pin configurations and conflicts</li><li>Protocol constraint enforcement (I2C addresses, UART baudrates, bus speeds)</li><li>Prevention of short-circuits and invalid connections</li><li>Power budget analysis with battery runtime estimation</li><li>Pin function oversubscription warnings (e.g., using an I2C pin as GPIO)</li><li>User-defined CONSTRAINT expressions with arithmetic, aggregates, and custom error messages</li><li>ALERT triggers with threshold conditions and automated actions</li></ul> |
| ⚙️ | **Automated Synthesis** | <ul><li>Generation of platform-specific code (Python/RiotOS) from abstract models</li><li>Automatic boilerplate generation for communication and hardware initialization</li><li>Consistent and error-free implementation artifacts</li></ul> |
| 🌐 | **Protocol-Agnostic** | <ul><li>Abstract definition of communication logic</li><li>Seamless switching between MQTT, AMQP, and Redis brokers</li><li>Multiple brokers with selective VIA routing per connection</li><li>Decoupled application logic from transport implementation</li></ul> |
| 🧩 | **Declarative Design** | <ul><li>High-level syntax for defining device composition</li><li>Separation of concerns between hardware, logic, and communication</li><li>Model-Driven Engineering (MDE) principles</li><li>SAMPLING blocks for declarative data acquisition configuration (rate, mode, buffering)</li></ul> |
| 🔧 | **IDE Integration** | <ul><li>Language Server Protocol (LSP) for real-time diagnostics, completion, hover, and go-to-definition</li><li>Works with VS Code, Neovim, Emacs, and any LSP-compatible editor</li><li>Start with `demol lsp`</li></ul> |
| ⚡ | **SmartConnect** | <ul><li>Automatic pin assignment for peripherals — no manual wiring needed</li><li>Resolves power and data connections based on peripheral requirements</li><li>Generates pin-mapping reports for visibility into auto-resolved connections</li></ul> |

---

## Quick Start

### Installation

```sh
git clone https://github.com/robotics-4-all/demol.git
cd demol
python -m venv venv && source ./venv/bin/activate
pip install -e .
```

## Example

```
DEVICE WeatherStation WITH description="Outdoor weather monitor", author="DeMoL", os=raspbian;

USE RaspberryPi_5_8GB;
USE BME680(EnvSensor), HCSR04(DistanceSensor);

NETWORK[WiFi] WITH ssid="IoT_Net", password="secure123";
BROKER[MQTT] Cloud WITH host="mqtt.example.com", port=1883;
BROKER[MQTT] Local WITH host="localhost", port=1883;

// Manual wiring — full control over pin assignments
CONNECT EnvSensor WITH
    POWER GND_1 -- gnd, power_5v_a -- vcc
    DATA i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl
    @ "sensors/environment"
    VIA Cloud;

// SmartConnect — automatic pin resolution (defaults to first broker)
SMARTCONNECT DistanceSensor @ "sensors/distance";

// Sampling configuration — declarative data acquisition
SAMPLING EnvSensor WITH rate = 10 hz, mode = continuous;
SAMPLING DistanceSensor WITH rate = 5 hz, mode = on_change, threshold = 0.1;

// User-defined constraints — domain-specific invariants
CONSTRAINT min_sensors: count(SENSOR) >= 2
    MESSAGE "At least 2 sensors required for redundancy";
CONSTRAINT power_budget: sum_power(PERIPHERAL) < 5 W;

// Alert triggers — threshold-based actions
ALERT frost_warning ON EnvSensor WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/frost" VIA Cloud
    COOLDOWN 60 hz;
```

Validate and generate:

```sh
demol validate examples/rpi/rpi_mixed_connect.dev
demol generate rpi examples/rpi/rpi_mixed_connect.dev --output-dir ./output
demol generate pinmap examples/rpi/rpi_mixed_connect.dev --output-dir ./output
```

## CLI

```
demol validate <model.dev>                              # Validate a device model
demol validate <model.dev> --skip-semantics             # Validate, ignore semantic errors
demol generate rpi <model.dev> --output-dir <dir>       # Generate Raspberry Pi Python code
demol generate riot <model.dev> --output-dir <dir>      # Generate RiotOS C code
demol generate svg <model.dev> --output-dir <dir>       # Generate wiring diagram (SVG)
demol generate docs <model.dev> --output-dir <dir>      # Generate hardware construction guide
demol generate pinmap <model.dev> --output-dir <dir>    # Generate pin-mapping report (MD + JSON)
demol generate json <model.dev> --output-dir <dir>      # Generate JSON representation
demol generate smauto <model.dev> --output-dir <dir>    # Generate SMAuto automation model
demol analyze power <model.dev>                         # Power consumption & battery autonomy report
demol analyze power <model.dev> --json-output           # Power analysis as JSON
demol fix <model.dev>                                   # Auto-fix common validation errors
demol fix <model.dev> --dry-run                         # Preview fixes without modifying the file
demol diff <model_a.dev> <model_b.dev>                  # Semantic diff between two models
demol diff <model_a.dev> <model_b.dev> --json-output    # Diff as JSON
demol lsp                                               # Start Language Server (LSP) for IDE integration
```

## Examples

The `examples/rpi/` directory contains ready-to-use device models demonstrating DeMoL features:

| Example | Features Demonstrated |
|---------|----------------------|
| [`rpi_greenhouse_sampling.dev`](examples/rpi/rpi_greenhouse_sampling.dev) | SAMPLING modes: continuous, on_change, batch |
| [`rpi_multi_broker_via.dev`](examples/rpi/rpi_multi_broker_via.dev) | Multiple BROKER declarations with VIA routing (edge vs cloud) |
| [`rpi_constraints_demo.dev`](examples/rpi/rpi_constraints_demo.dev) | User-defined CONSTRAINT expressions with `count()`, `sum_power()` |
| [`rpi_battery_power_analysis.dev`](examples/rpi/rpi_battery_power_analysis.dev) | POWERSOURCE + `demol analyze power` for battery runtime estimation |
| [`rpi_alert_triggers.dev`](examples/rpi/rpi_alert_triggers.dev) | ALERT triggers with `&&` conditions, ACTIVATE, PUBLISH VIA, COOLDOWN |
| [`rpi_all_features.dev`](examples/rpi/rpi_all_features.dev) | **All features combined**: sampling, multi-broker VIA, constraints, alerts, battery |
| [`rpi_mixed_connect.dev`](examples/rpi/rpi_mixed_connect.dev) | Manual CONNECT + SmartConnect in the same model |
| [`rpi_smart_home.dev`](examples/rpi/rpi_smart_home.dev) | Multi-peripheral smart home (I2C, GPIO, TTS) |
| [`multi_periph.dev`](examples/rpi/multi_periph.dev) | Complex system with 5 peripherals |

## Hardware Library

DeMoL ships with a built-in hardware library of boards and peripherals. Each entry is a validated `.hwd` component model that the DSL resolves at parse time.

### Supported Boards

| DSL Identifier | Family | VCC | I/O Voltage | RAM | CPU / MCU | Code Targets |
|---|---|---|---|---|---|---|
| `RaspberryPi_5_8GB` | Raspberry Pi | 5 V | 3.3 V | 8 GB | ARM Cortex-A76 | RPi Python |
| `RaspberryPi_4B_8GB` | Raspberry Pi | 5 V | 3.3 V | 8 GB | ARM Cortex-A72 | RPi Python |
| `RaspberryPi_4B_4GB` | Raspberry Pi | 5 V | 3.3 V | 4 GB | ARM Cortex-A72 | RPi Python |
| `RaspberryPi_3B_Plus` | Raspberry Pi | 5 V | 3.3 V | 1 GB | ARM Cortex-A53 | RPi Python |
| `RaspberryPi_3B` | Raspberry Pi | 5 V | 3.3 V | 1 GB | ARM Cortex-A53 | RPi Python |
| `RaspberryPi_3A_Plus` | Raspberry Pi | 5 V | 3.3 V | 512 MB | ARM Cortex-A53 | RPi Python |
| `RPiPico` | Raspberry Pi | 5 V | 3.3 V | 264 KB | RP2040 | RPi Python |
| `ESP32Wroom32` | ESP | 5 V | 3.3 V | 520 KB | ESP32 | RIOT C |
| `NodeMCU_ESP8266` | ESP | 3.3 V | 3.3 V | 80 KB | ESP8266 | RIOT C |
| `WemosD1Mini` | ESP | 5 V | 3.3 V | 80 KB | ESP8266 | RIOT C |
| `WemosD1R32` | ESP | 5 V | 3.3 V | 520 KB | ESP32 | RIOT C |
| `ArduinoUno` | Arduino | 5 V | 5 V | 2 KB | ATmega328P | RIOT C |

### Supported Peripherals

#### Sensors

| DSL Identifier | Category | Interface | Description | RPi Python | RIOT C |
|---|---|---|---|---|---|
| `BME280` | Environmental | I²C | Temperature, humidity, pressure | ✓ | — |
| `BME680` | Environmental | I²C | Temperature, humidity, pressure, air quality | ✓ | ✓ |
| `DHT22` | Environmental | GPIO | Temperature and humidity (1-wire) | ✓ | — |
| `Mpl3115a2` | Environmental | I²C | Barometric pressure and altitude | ✓ | ✓ |
| `SHTC3` | Environmental | I²C | High-precision temperature and humidity | ✓ | — |
| `MPU6050` | IMU | I²C | 6-axis accelerometer + gyroscope | ✓ | — |
| `QMC5883L` | IMU | I²C | 3-axis magnetometer / compass | ✓ | — |
| `BH1750` | Light | I²C | Ambient light intensity (lux) | ✓ | — |
| `APDS9960` | Light | I²C | Gesture, proximity, RGB color and ambient light | ✓ | — |
| `DS18B20` | Temperature | GPIO | 1-wire digital temperature probe | ✓ | — |
| `MLX90614` | Temperature | I²C | IR non-contact thermometer | ✓ | — |
| `MQ2` | Gas | GPIO (ADC) | Smoke, LPG, CO gas detection | ✓ | — |
| `CCS811` | Gas | I²C | Air quality sensor (eCO2 + TVOC) | ✓ | — |
| `ADCDifferentialPi` | ADC | I²C | 8-channel 18-bit differential ADC | ✓ | ✓ |
| `ADS1115` | ADC | I²C | 16-bit 4-channel ADC | ✓ | — |
| `HCSR04` | Distance | GPIO | Ultrasonic distance (2 cm – 4 m) | ✓ | ✓ |
| `HCSR04P` | Distance | GPIO | Ultrasonic distance (low-power variant) | ✓ | ✓ |
| `SRF04` | Distance | GPIO | Ultrasonic distance sensor | ✓ | ✓ |
| `SRF05` | Distance | GPIO | Ultrasonic distance (extended range) | ✓ | ✓ |
| `TFMini` | Distance | UART | LiDAR distance sensor (0.3 m – 12 m) | ✓ | ✓ |
| `VL53L1X` | Distance | I²C | ToF laser ranging (up to 4 m) | ✓ | ✓ |
| `PIR_HCSR501` | Proximity | GPIO | Passive infrared motion detector | ✓ | — |
| `HW006` | Proximity | GPIO | IR proximity / obstacle detection | ✓ | ✓ |
| `TCRT5000` | Proximity | GPIO | Reflective IR line sensor | ✓ | ✓ |
| `TactileButton` | Input | GPIO | Momentary push button | ✓ | ✓ |
| `SoilMoisture` | Humidity | GPIO (ADC) | Capacitive soil moisture sensor | ✓ | — |
| `INA219` | Power | I²C | Current and power monitor | ✓ | — |
| `DS3231` | RTC | I²C | Real-time clock with temperature compensation | ✓ | — |
| `NEOM6GPS` | GPS | UART | u-blox NEO-6M GPS module (NMEA) | ✓ | — |
| `HX711` | Weight | GPIO | 24-bit load cell amplifier | ✓ | — |
| `MFRC522` | RFID | SPI | 13.56 MHz RFID reader/writer | ✓ | — |
| `MAX30102` | Bio | I²C | Pulse oximeter and heart rate monitor | ✓ | — |

#### Actuators

| DSL Identifier | Category | Interface | Description | RPi Python | RIOT C |
|---|---|---|---|---|---|
| `LedGeneric` | LED | GPIO | Single-colour digital LED | ✓ | ✓ |
| `WS2812` | LED Array | GPIO (PWM) | Addressable RGB LED strip (NeoPixel) | ✓ | ✓ |
| `WS281X` | LED Array | GPIO (PWM) | Addressable RGB LED strip (WS281x family) | ✓ | ✓ |
| `ServoGeneric` | Servo | GPIO (PWM) | Generic RC servo motor | ✓ | ✓ |
| `PCA9685` | Servo Controller | I²C | 16-channel 12-bit PWM driver | ✓ | ✓ |
| `MotorGeneric` | DC Motor | GPIO (PWM) | Brushed DC motor via H-bridge | ✓ | ✓ |
| `L298N` | Motor Driver | GPIO (PWM) | Dual H-bridge DC motor driver | ✓ | — |
| `A4988` | Stepper Driver | GPIO | Stepper motor driver (step/direction) | ✓ | — |
| `RelayModule` | Relay | GPIO | Optocoupler relay module | ✓ | — |
| `BuzzerGeneric` | Buzzer | GPIO | Passive/active piezo buzzer | ✓ | ✓ |
| `SSD1306` | Display | I²C | 128×64 OLED display | ✓ | — |
| `NRF24L01` | Wireless | SPI | 2.4 GHz wireless transceiver | ✓ | — |
| `TTSSpeaker` | Audio | GPIO | Text-to-speech speaker (Piper TTS) | ✓ | — |

### Power Sources

| DSL Identifier | Type | Voltage | Capacity | Max Current |
|---|---|---|---|---|
| `li_ion_3v7` | Li-Ion Battery | 3.7 V | 2 500 mAh | 2 A |
| `usb_power_bank` | USB Power Bank | 5 V | 10 000 mAh | 2.4 A |

## Development

### Make Targets

```sh
make ci                  # Run full CI pipeline in a Docker container
make ci-check            # Run full CI pipeline locally (no Docker)
make test                # Run pytest tests only
make test-local          # Run pytest + validation scripts + transformation scripts
make test-cov            # Run tests with HTML coverage report
make lint                # Run flake8 linting
make format              # Format code with black
make format-check        # Check formatting without modifying files
make type-check          # Run mypy type checking
make validate-examples   # Validate all example .dev models
make check               # Run lint + type-check + test-local
```

### CI/CD

The project uses **GitHub Actions** for continuous integration. Every push and pull request to `main`, `master`, or `devel` triggers:

| Job | Description |
|-----|-------------|
| **Lint & Format** | `black --check` and `flake8` on Python 3.11 |
| **Type Check** | `mypy` with `--ignore-missing-imports` |
| **Test** | `pytest` across Python 3.9, 3.10, 3.11, 3.12, 3.13 |
| **Validate Examples** | `demol validate` on all `.dev` files in `examples/` |

Run the same pipeline locally in a container with `make ci`, or directly with `make ci-check`.

### Test Suite

The test suite covers 315+ tests across:

| Category | Tests | Coverage |
|----------|-------|----------|
| Semantic validators | 140+ | All 21 validation rules (power, pins, protocols, constraints, alerts, sampling, brokers) |
| Parser robustness | 57 | Empty input, malformed syntax, boundary values, truncated models, encoding, edge cases |
| Code generation | 30+ | RPi Python, RiotOS C, SAMPLING integration, JSON serialization |
| CLI commands | 26+ | Auto-fix, model diff, power analysis |
| LSP server | 16 | Diagnostics, completion, hover, go-to-definition |
| Performance | 5 | Parse/validate timing with regression thresholds |
| SmartConnect | 25+ | Automatic pin resolution, protocol classification |

### Error Messages

The CLI translates parser internals into domain-friendly messages with actionable hints:

```
[!] Syntax Error
  Location: model.dev:5:42
  Expected ';' => 'USE BME680*[Sensor1]'
  Hint: Missing semicolon at end of statement.
```

## Documentation

| Document | Description |
|----------|-------------|
| [Language Reference](docs/language-reference.md) | Grammar, syntax, hardware components, connections, brokers |
| [Semantic Validation](docs/semantic-validation.md) | Validation rules, safety checks, error examples |
| [Code Generation & CLI](docs/code-generation.md) | Generators, CLI usage, deployment artifacts, diagrams |
| [Formal Semantics](docs/semantics.md) | Mathematical specification of the language |
| [Sensors & Actuators](docs/sensors-actuators.md) | 35 sensor types, 23 actuator types, message schemas |
| [Testing](docs/testing.md) | Test suite structure and coverage |

## License

DeMoL is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).
