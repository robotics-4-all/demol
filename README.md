<div align="center">

![DeMoL](https://github.com/robotics-4-all/demol/blob/main/assets/demol_logo.png)

**A textX-based DSL for hardware-aware IoT device modeling with automated code generation, semantic validation, and visual design.**

<img src="https://img.shields.io/badge/Python-3776AB.svg?style=default&logo=Python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/textX-2496ED.svg?style=default&logo=textx&logoColor=white" alt="textX">
<img src="https://img.shields.io/badge/FastAPI-2496ED.svg?style=default&logo=FastAPI&logoColor=white" alt="FastAPI">
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
| 🛡️ | **Semantic Safety** | <ul><li>Rigorous validation of pin configurations and conflicts</li><li>Protocol constraint enforcement (I2C addresses, UART baudrates)</li><li>Prevention of short-circuits and invalid connections</li></ul> |
| ⚙️ | **Automated Synthesis** | <ul><li>Generation of platform-specific code (Python/RiotOS) from abstract models</li><li>Automatic boilerplate generation for communication and hardware initialization</li><li>Consistent and error-free implementation artifacts</li></ul> |
| 🌐 | **Protocol-Agnostic** | <ul><li>Abstract definition of communication logic</li><li>Seamless switching between MQTT, AMQP, and Redis brokers</li><li>Decoupled application logic from transport implementation</li></ul> |
| 🧩 | **Declarative Design** | <ul><li>High-level syntax for defining device composition</li><li>Separation of concerns between hardware, logic, and communication</li><li>Model-Driven Engineering (MDE) principles</li></ul> |
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

### Docker

Start the full stack (API + Visual Designer):

```sh
./start.sh
```

## Example

```
DEVICE WeatherStation WITH description="Outdoor weather monitor", author="DeMoL", os=raspbian;

USE RaspberryPi_5_8GB;
USE BME680(EnvSensor), HCSR04(DistanceSensor);

NETWORK[WiFi] WITH ssid="IoT_Net", password="secure123";
BROKER[MQTT] Cloud WITH host="mqtt.example.com", port=1883;

// Manual wiring — full control over pin assignments
CONNECT EnvSensor WITH
    POWER GND_1 -- gnd, power_5v_a -- vcc
    DATA i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl
    @ "sensors/environment";

// SmartConnect — automatic pin resolution
SMARTCONNECT DistanceSensor @ "sensors/distance";
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
```

## Documentation

| Document | Description |
|----------|-------------|
| [Language Reference](docs/language-reference.md) | Grammar, syntax, hardware components, connections, brokers |
| [Semantic Validation](docs/semantic-validation.md) | Validation rules, safety checks, error examples |
| [Code Generation & CLI](docs/code-generation.md) | Generators, CLI usage, deployment artifacts, diagrams |
| [REST API](docs/api.md) | Validation and generation endpoints |
| [Formal Semantics](docs/semantics.md) | Mathematical specification of the language |
| [Sensors & Actuators](docs/sensors-actuators.md) | 35 sensor types, 23 actuator types, message schemas |
| [Testing](docs/testing.md) | Test suite structure and coverage |

## License

DeMoL is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).
