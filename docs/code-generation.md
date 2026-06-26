# Code Generation & CLI Usage

## CLI Overview

The DeMoL CLI provides commands for validating device models and generating platform-specific code, documentation, and diagrams.

```
Usage: demol [OPTIONS] COMMAND [ARGS]...

  DeMoL CLI - A DSL for modeling IoT Devices

Options:
  --help  Show this message and exit.

Commands:
  generate  Generate code, documentation, or diagrams from a model
  validate
```

### Validate Command

Validates a device model for syntax correctness and semantic safety:

```sh
demol validate examples/rpi/multi_periph.dev
```

**Successful output:**
```
[*] Running validation for model examples/rpi/multi_periph.dev
[✓] Validation passed!
```

### Generate Command

Executes Model-to-Text (M2T) transformations to generate code, documentation, or diagrams:

```sh
demol generate [GENERATOR] [MODEL_FILE] --output-dir [DIR]
```

**Available Generators:**

| Generator | Output | Description |
|-----------|--------|-------------|
| `rpi` | Python | Raspberry Pi code (RPi.GPIO, smbus2, spidev) |
| `riot` | C | RiotOS code for embedded systems |
| `zephyr` | C + devicetree | Zephyr RTOS code with CMakeLists.txt, prj.conf, devicetree overlay |
| `wokwi` | diagram.json + wokwi.toml | Wokwi web simulator project |
| `renode` | .repl + pyrenode3 | Renode hardware emulator |
| `svg` | SVG | Wiring diagram |
| `svg --infrastructure` | SVG | Infrastructure diagram (Edge/Communication/Application layers) |
| `docs` | Markdown | Hardware construction guide with BOM and wiring tables |
| `pinmap` | Markdown + JSON | Pin-mapping report showing resolved connections |
| `json` | JSON | JSON representation of the model |
| `smauto` | SMAuto DSL | SMAuto model for automation |

## Code Generation

DeMoL supports automated code generation for multiple platforms using a model-driven architecture.

### Architecture

![DeMoL Runtime Architecture](../assets/DeMoL_Runtime_Conceptual_nobg.png)

The code generation system uses an abstract `BaseCodeGenerator` class that provides common model querying capabilities. Platform-specific generators inherit from this base class to implement target-specific logic.

```
Device Model → BaseCodeGenerator (abstract)
                    ↓
            ┌───────┴────────────────────┐
            ↓                ↓            ↓
    RPiCodeGenerator    RiotCodeGenerator  ZephyrCodeGenerator
            ↓                ↓            ↓
    WokwiCodeGenerator    RenodeCodeGenerator
            ↓                ↓            ↓
        Templates        Templates      Templates
```

### Supported Generators

- **Raspberry Pi (Python)**: Generates Python code using `RPi.GPIO`, `smbus2`, and `spidev`. Full AMQP (pika) and Redis (redis-py) broker support. CONSTRAINT runtime via `constraints.py`.
- **RiotOS (C)**: Generates C code for RiotOS-supported boards. CONSTRAINT runtime via `constraint.c`/`constraint.h`. Broker stubs with TODO markers.
- **Zephyr RTOS (C)**: Generates a complete Zephyr application: `CMakeLists.txt`, `prj.conf`, devicetree overlay, `main.c`, and one driver source file per peripheral. 18 driver templates covering BME680, BME280, BH1750, DS18B20, DHT22, PIR_HCSR501, relay, servo, ADS1115, SHTC3, HW006, button, HCSR04, LED, MPL3115A2, SRF04, SRF05, WS281X. CONSTRAINT runtime via `constraint.c`/`constraint.h`. Broker stubs.
- **Wokwi (diagram.json)**: Generates a `diagram.json` + `wokwi.toml` for the Wokwi web simulator. Maps device model parts to standard Wokwi component IDs.
- **Renode (.repl)**: Generates a `.repl` platform description + `pyrenode3` test script for the Renode hardware emulator.

### Running Code Generation

```sh
# Generate Raspberry Pi code
demol generate rpi examples/rpi/multi_periph.dev --output-dir ./rpi_code

# Generate code even if semantic validation fails
demol generate rpi examples/rpi/multi_periph.dev --skip-semantics --output-dir ./rpi_code
```

This will:
1. Parse the device model
2. Validate semantics
3. Resolve platform-specific templates
4. Generate the runtime software for the device
5. **Generate deployment artifacts**:
   - `Dockerfile`: For containerized deployment
   - `docker-compose.yml`: For orchestrating the device and its broker
   - `requirements.txt`: For Python dependencies
   - `install_deps.sh`: A standalone bash script to install all `apt` and `pip` dependencies directly on the host system (non-Docker deployment)

## CONSTRAINT Code Generation

The CONSTRAINT block generates platform-specific runtime check code:

- **RPi (Python)**: Emits `constraints.py` with a `ConstraintEvaluator` class that evaluates `count()` and `sum_power()` expressions against live sensor data
- **RIOT (C)**: Emits `constraint.c`/`constraint.h` with static evaluation functions using `xtimer` for periodic checks
- **Zephyr (C)**: Emits `constraint.c`/`constraint.h` with Zephyr-native timer integration

```sh
demol generate rpi examples/rpi/rpi_constraint_bme.dev --output-dir ./output
demol generate riot examples/esp/wemos_constraint_bme680.dev --output-dir ./output
demol generate zephyr examples/esp/wemos_constraint_bme680.dev --output-dir ./output
```

## Broker Support

The BROKER block generates transport-specific connection code:

- **MQTT**: Full support on all platforms (default broker)
- **AMQP**: Full support on RPi (via `pika`), stubs on RIOT/Zephyr
- **Redis**: Full support on RPi (via `redis-py`), stubs on RIOT/Zephyr

```sh
demol generate rpi examples/rpi/rpi_amqp_bme680.dev --output-dir ./output
demol generate rpi examples/rpi/rpi_redis_bme680.dev --output-dir ./output
```

## Pin-Mapping Reports

Generate pin-mapping reports showing resolved pin assignments for device models. This is especially useful for SmartConnect models where pins are auto-assigned and not visible in the source `.dev` file.

```sh
demol generate pinmap examples/rpi/rpi_smart_connect.dev --output-dir ./output
```

This generates two files:
- **Markdown** (`<DeviceName>_pinmap.md`) — Human-readable tables with power/data sections per peripheral, protocol details, and SmartConnect badges
- **JSON** (`<DeviceName>_pinmap.json`) — Machine-readable structured data with board pin numbers, protocol properties, and connection source (manual vs smartconnect)

## Documentation & Diagram Generation

### Hardware Construction Guide

Generates a Markdown file with BOM, wiring tables, and communication details:

```sh
demol generate docs examples/rpi/multi_periph.dev --output-dir ./docs
```

### System Diagram (Wiring)

Generates a hardware-aware diagram showing pin-to-pin connections:

```sh
demol generate svg examples/rpi/multi_periph.dev --output-dir ./diagrams
```

**Output Example:**

![System Diagram](../assets/MultiPeriphDevice.svg)

### Infrastructure Diagram

Generates a diagram visualizing the Edge, Communication, and Application layers:

```sh
demol generate svg examples/rpi/multi_periph.dev --infrastructure --output-dir ./diagrams
```

**Output Example:**

![Infrastructure Diagram](../assets/MultiPeriphDevice_infrastructure.svg)

## Skipping Semantic Validation

If you want to generate code even if semantic rules are failing (e.g., for testing or partial code generation), use the `--skip-semantics` flag:

```sh
demol generate rpi examples/rpi/multi_periph.dev --skip-semantics --output-dir ./rpi_code
demol generate svg examples/rpi/multi_periph.dev --skip-semantics --output-dir ./diagrams
```

This will report all errors but return a success exit code, allowing the process to continue. For details on validation rules, see [Semantic Validation](semantic-validation.md).
