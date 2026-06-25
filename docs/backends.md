# Backend Reference

DeMoL ships with five code generators, each producing a complete runnable artifact
set for one target platform or simulator. The CLI subcommand selects the backend;
the `.dev` model is unchanged. All backends share the same validated model, the
same pin assignments, the same broker configuration, and the same topic wiring.

| Backend | CLI subcommand | Output language | Target |
| --- | --- | --- | --- |
| Raspberry Pi | `demol generate rpi` | Python (commlib-py) | Raspbian on Raspberry Pi |
| RIOT OS | `demol generate riot` | C | RIOT OS on ESP32 / ESP8266 |
| Zephyr RTOS | `demol generate zephyr` | C + devicetree | Zephyr on ESP32 / ESP8266 |
| Wokwi | `demol generate wokwi` | `diagram.json` + `wokwi.toml` | Wokwi web simulator |
| Renode | `demol generate renode` | `.repl` + pyrenode3 | Renode hardware simulator |

This document covers the full reference for each backend. The RPi and RIOT
sections summarise the existing generators; the Zephyr, Wokwi, and Renode
sections document the new backends added during the multi-backend evolution.

## Table of Contents

- [Raspberry Pi (`rpi`)](#raspberry-pi-rpi)
- [RIOT OS (`riot`)](#riot-os-riot)
- [Zephyr RTOS (`zephyr`)](#zephyr-rtos-zephyr)
- [Wokwi (`wokwi`)](#wokwi-wokwi)
- [Renode (`renode`)](#renode-renode)
- [Peripheral Support Matrix](#peripheral-support-matrix)

---

## Raspberry Pi (`rpi`)

### Overview

The RPi generator emits a complete Python application for a Raspberry Pi running
Raspbian. The application uses the [commlib-py](https://github.com/robotics-4-all/commlib-py)
messaging library, the [RPi.GPIO](https://pypi.org/project/RPi.GPIO/) library
for GPIO access, [smbus2](https://pypi.org/project/smbus2/) for I2C, and
[spidev](https://pypi.org/project/spidev/) for SPI. A Docker-based deployment
story ships alongside the code: a `Dockerfile`, `docker-compose.yml`,
`requirements.txt`, and `install_deps.sh` script.

The generator is the original DeMoL codegen target and has the broadest
peripheral support of all backends. It is the byte-identical regression baseline
for the multi-backend evolution: RPi output is checked against golden-file
snapshots on every CI run.

### CLI Usage

```sh
demol generate rpi <model.dev> --output-dir <dir> [--skip-semantics]
```

| Flag | Required | Description |
| --- | --- | --- |
| `model_filepath` (positional) | yes | Path to the `.dev` model |
| `--output-dir` | no | Output directory (default: current directory) |
| `--skip-semantics` | no | Generate even if semantic rules are failing |

### Output Structure

```
<output-dir>/
├── <peripheral>_<instance>.py     # one driver file per peripheral instance
├── <instance>_node.py             # one commlib node per instance
├── msg.py                         # message classes (per topic)
├── common.py                      # shared helpers
├── alerts.py                      # ALERT trigger runtime
├── Dockerfile                     # Python deployment image
├── docker-compose.yml             # broker + app composition
├── requirements.txt               # pinned Python dependencies
└── install_deps.sh                # system package installation
```

### Supported Peripherals

The full RPi peripheral template library lives in
[`demol/templates/rpi/`](../demol/templates/rpi/). The library covers every
board, sensor, actuator, and power source in the hardware catalog. Refer to
[`docs/sensors-actuators.md`](sensors-actuators.md) for the complete list with
interface type, bus protocol, and voltage range for each component.

### Example

```sh
demol generate rpi examples/rpi/rpi_mixed_connect.dev --output-dir ./rpi_out
```

The generator produces `envsensor_node.py` (commlib node), a per-peripheral
driver module (e.g. `bme680_envsensor.py`), a `msg.py` defining the MQTT
payload schema, and a complete Docker deployment manifest.

---

## RIOT OS (`riot`)

### Overview

The RIOT generator emits a complete C application for [RIOT OS](https://www.riot-os.org/).
The output targets ESP32 and ESP8266 boards and uses a single MQTT client. Each
peripheral produces a paired `sensor_<name>_<idx>.{c,h}` or
`actuator_<name>_<idx>.{c,h}` driver. A `Makefile` referencing `$(RIOTBASE)`,
a `Dockerfile.riotbuild`, and a `build_docker.sh` script ship alongside the
source so end users can build firmware without a local RIOT checkout. The
build script auto-clones RIOT inside the container and pins the image to
`demol/riotbuild:<version>`.

### CLI Usage

```sh
demol generate riot <model.dev> --output-dir <dir> [--skip-semantics]
```

| Flag | Required | Description |
| --- | --- | --- |
| `model_filepath` (positional) | yes | Path to the `.dev` model |
| `--output-dir` | no | Output directory (default: current directory) |
| `--skip-semantics` | no | Generate even if semantic rules are failing |

The RIOT version and source repository are env-overridable at generation time
via `DEMOL_RIOT_VERSION` and `DEMOL_RIOT_REPO`. Set `DEMOL_RIOT_SKIP_MISSING=1`
only if intentional template-skipping is required; the generator is otherwise
fail-fast on missing templates.

### Output Structure

```
<output-dir>/
├── main.c                         # entry point, init, main loop
├── Makefile                       # references $(RIOTBASE)
├── mqtt_broker.{c,h}              # MQTT client wrapper
├── json_handler.{c,h}             # JSON payload encoding
├── sensor_<name>_<idx>.{c,h}      # one driver pair per sensor
├── actuator_<name>_<idx>.{c,h}    # one driver pair per actuator
├── Dockerfile.riotbuild           # self-contained build image
└── build_docker.sh                # auto-builds demol/riotbuild:<version>
```

### Supported Peripherals

The RIOT driver library lives in
[`demol/templates/riot/`](../demol/templates/riot/). It ships 18 driver
pairs covering the most common IoT peripherals: `bme680`, `bme280`, `bh1750`,
`hw006` (HCSR04 variant), `mpl3115a2`, `srf04`, `srf05`, `ds18b20`, `dht22`,
`pir_hcsr501`, `relay`, `servo`, `ads1115`, `shtc3`, `led`, `ws281x`, and `button`.
Peripherals outside this set fall back to a generic GPIO template; for full
hardware coverage, the RPi backend is the recommended target.

### Example

```sh
demol generate riot examples/esp/esp_iot_device.dev --output-dir ./riot_out
```

The generator produces a complete RIOT application. Build it with
`./riot_out/build_docker.sh`; the script clones RIOT inside the image, runs
`make` against the project's `Makefile`, and produces a flashable `bin/`
artifact.

---

## Zephyr RTOS (`zephyr`)

### Overview

The Zephyr generator emits a complete [Zephyr](https://zephyrproject.org/)
application. The output includes a `CMakeLists.txt`, a `prj.conf` Kconfig
fragment, a board-specific devicetree overlay, a static `main.c` skeleton, and
one driver source file per peripheral instance. The driver set covers the most
common IoT peripherals; the generated application compiles against the Zephyr
SDK and is flashable with `west flash`.

The generator is targeted at ESP32 and ESP8266 boards, where Zephyr has the
strongest upstream support. The board is inferred from the model's `USE`
board declaration and can be overridden via the `--board` flag.

### CLI Usage

```sh
demol generate zephyr <model.dev> --output-dir <dir> [--board <name>] [--skip-semantics]
```

| Flag | Required | Description |
| --- | --- | --- |
| `model_filepath` (positional) | yes | Path to the `.dev` model |
| `--output-dir` | no | Output directory (default: current directory) |
| `--board` | no | Override Zephyr board name (e.g. `esp32_devkitc`) |
| `--skip-semantics` | no | Generate even if semantic rules are failing |

The inferred board mapping (DeMoL board → Zephyr board) is:

| DeMoL board | Zephyr board |
| --- | --- |
| `RaspberryPi_4_Model_B` (any variant) | `rpi_4b` |
| `RaspberryPi_5_8GB` | `rpi_5` |
| `ESP32Wroom32` | `esp32_devkitc` |
| `WemosD1R32` | `esp32_devkitc` |
| `NodeMCUESP8266` | `esp8266` |
| `WemosD1Mini` | `esp8266` |
| `ArduinoUno` | `arduino_uno` |

### Output Structure

```
<output-dir>/
└── app/
    ├── CMakeLists.txt
    ├── prj.conf
    ├── boards/<board>.overlay      # devicetree overlay, e.g. esp32_devkitc.overlay
    ├── src/
    │   ├── main.c                  # static skeleton: init, main loop
    │   └── <peripheral>.c          # one driver file per peripheral instance
    └── dts/bindings/.gitkeep
```

### Supported Peripherals

The Zephyr driver library lives in
[`demol/templates/zephyr/`](../demol/templates/zephyr/). It ships 18 drivers:

| Peripheral | Bus | Notes |
| --- | --- | --- |
| `bme680` | I2C | Environmental sensor (T, P, H, gas) |
| `bme280` | I2C | Environmental sensor (T, P, H) |
| `bh1750` | I2C | Ambient light sensor (lux) |
| `ds18b20` | GPIO (1-Wire) | Temperature sensor (timing-sensitive) |
| `dht22` | GPIO | Temperature + humidity sensor (timing-sensitive) |
| `pir_hcsr501` | GPIO | PIR motion sensor (digital output) |
| `relay` | GPIO | Digital relay output (on/off) |
| `servo` | PWM | Servo motor (PWM 50Hz) |
| `ads1115` | I2C | 16-bit 4-channel ADC |
| `shtc3` | I2C | Temperature + humidity sensor |
| `hw006` | GPIO | IR proximity sensor (digital output) |
| `button` | GPIO | Tactile / pushbutton input |
| `hcsr04` | GPIO | Ultrasonic distance sensor |
| `led` | GPIO | Single-color LED output |
| `mpl3115a2` | I2C | Pressure / altitude sensor |
| `srf04` | GPIO | Ultrasonic distance sensor |
| `srf05` | GPIO | Ultrasonic distance sensor |
| `ws281x` | SPI | Addressable RGB LED chain |

### Example

```sh
demol generate zephyr examples/esp/esp_bme680.dev --output-dir ./zephyr_out
```

The generator writes `app/` into `./zephyr_out/`. Build with
`west build -b esp32_devkitc app/`, then flash with `west flash`. The
peripheral driver sources in `app/src/` are the integration point: each one
exposes a `peripheral_init()`, `peripheral_read()`, and `peripheral_publish()`
interface that `main.c` calls from the sampling loop.

---

## Wokwi (`wokwi`)

### Overview

The Wokwi generator emits a [Wokwi](https://wokwi.com/) simulation project
from the `.dev` model. The output is a `diagram.json` describing the parts
and their connections plus a `wokwi.toml` for net colour configuration.
Wokwi loads the project in the browser and provides a fully interactive
circuit simulation: pins can be driven from a Wokwi logic analyser, code can
run on the simulated microcontroller, and serial / I2C / SPI traffic is
captured in the protocol analyser pane.

The generator maps DeMoL component types to canonical Wokwi part IDs. The
mapping table is defined in
[`demol/transformations/m2t_wokwi.py`](../demol/transformations/m2t_wokwi.py)
in the `_BOARD_PART_IDS` and `_PERIPHERAL_PART_IDS` dictionaries. Unmapped
components fall back to a generic placeholder so the diagram still loads in
the simulator and the user can swap the part type in the JSON.

### CLI Usage

```sh
demol generate wokwi <model.dev> --output-dir <dir> [--skip-semantics]
```

| Flag | Required | Description |
| --- | --- | --- |
| `model_filepath` (positional) | yes | Path to the `.dev` model |
| `--output-dir` | no | Output directory (default: current directory) |
| `--skip-semantics` | no | Generate even if semantic rules are failing |

### Output Structure

```
<output-dir>/
├── diagram.json                   # parts[] + connections[] derived from model
└── wokwi.toml                     # [wokwi] version + [net] color table
```

The `diagram.json` is a Wokwi v1 diagram:

```json
{
  "version": 1,
  "author": "DeMoL",
  "editor": "wokwi",
  "parts": [
    { "type": "board-raspberry-pi-4b", "id": "rpi", ... },
    { "type": "bme680", "id": "envsensor", ... }
  ],
  "connections": [
    { "from": "rpi:GND.1", "to": "envsensor:GND", "color": "black" }
  ]
}
```

The `wokwi.toml` declares the Wokwi project format version and a colour table
for the `i2c`, `spi`, `uart`, `gpio`, and `pwm` nets.

### Supported Peripherals

Wokwi support is component-mapped; every peripheral in the hardware library
maps to a Wokwi part if the part exists in the Wokwi catalog. The current
mapping covers eleven boards and sixteen peripherals:

| Board (DeMoL) | Wokwi board ID |
| --- | --- |
| `RaspberryPi_4_Model_B` (all variants) | `board-raspberry-pi-4b` |
| `RaspberryPi_5` | `board-raspberry-pi-5` |
| `RaspberryPi_Pico` | `wokwi-pi-pico` |
| `WemosD1Mini` / `WemosD1R32` | `board-wemos-d1-r32` |
| `ESP32Wroom32` | `board-esp32-devkit-c-v4` |
| `NodeMCUESP8266` | `wokwi-nodemcu` |
| `ArduinoUno` | `wokwi-arduino-uno` |

| Peripheral (DeMoL) | Wokwi part ID |
| --- | --- |
| `BME680` | `bme680` |
| `BME280` | `wokwi-bme280` |
| `LedGeneric` | `wokwi-led` |
| `TactileButton` | `wokwi-pushbutton` |
| `WS2812` | `wokwi-neopixel` |
| `HCSR04` | `wokwi-hc-sr04` |
| `SRF04` | `wokwi-hc-sr04` |
| `SRF05` | `wokwi-hc-sr05` |
| `MPL3115A2` | `wokwi-mpl3115a2` |
| `SSD1306` | `wokwi-ssd1306` |
| `DHT22` | `wokwi-dht22` |
| `DS18B20` | `wokwi-ds18b20` |
| `PIR_HCSR501` | `wokwi-pir` |
| `Buzzer` | `wokwi-buzzer` |
| `Relay` | `wokwi-relay-module` |
| `Servo` | `wokwi-servo` |

Peripherals not in the mapping fall back to a generic placeholder so the
diagram remains valid; the user can then substitute the appropriate Wokwi
part in the editor.

### Example

```sh
demol generate wokwi examples/esp/esp_button_led.dev --output-dir ./wokwi_out
```

The generator writes `diagram.json` and `wokwi.toml` into `./wokwi_out/`. Drop
the contents into the [Wokwi editor](https://wokwi.com/) or push them to a
GitHub repository connected to a Wokwi project; the circuit will load with
all parts pre-placed and all connections drawn.

---

## Renode (`renode`)

### Overview

The Renode generator emits a [Renode](https://renode.io/) simulation
harness from the `.dev` model. The output is a `.repl` platform description
that maps the board's CPU, buses, and peripheral devices onto Renode's
`sysbus`, plus a `pyrenode3` Python test script that boots the simulation,
loads the application ELF, and asserts that each declared peripheral is
present at runtime.

The Renode backend is verification-oriented: it provides fast, headless
integration tests for firmware before it is flashed to real hardware. The
generated test script can be executed in CI without physical hardware; Renode
emulates the CPU and peripherals, runs the firmware, and reports which
peripherals initialise correctly. This is the primary mechanism for
cross-backend testing in DeMoL's CI: a model compiles to RIOT C, Zephyr C,
Wokwi JSON, and Renode `.repl`/Python in one pass, and the Renode test
verifies that the firmware-implied peripheral topology matches the model.

### CLI Usage

```sh
demol generate renode <model.dev> --output-dir <dir> [--elf-path <path>] [--skip-semantics]
```

| Flag | Required | Description |
| --- | --- | --- |
| `model_filepath` (positional) | yes | Path to the `.dev` model |
| `--output-dir` | **yes** | Output directory (no default; must be provided) |
| `--elf-path` | no | Path to a pre-built firmware ELF for direct simulation boot |
| `--skip-semantics` | no | Generate even if semantic rules are failing |

The `--elf-path` flag is optional at generation time; the test script loads
the ELF at simulation time, and the path can be supplied to `pyrenode3` on
the command line or edited into `test_device.py` before running.

### Output Structure

```
<output-dir>/
├── device.repl                    # platform description: sysbus, CPU, peripherals
└── test_device.py                 # pyrenode3 driver: load + assert peripheral topology
```

The `.repl` file uses Renode's standard platform description syntax:

```
using sysbus
mach create
machine LoadPlatformDescription @platforms/esp32.repl
sysbus LoadELF @<elf_path>
```

The `test_device.py` script is a `pyrenode3` driver. It boots the
simulation, loads the application ELF, and emits one test per declared
peripheral:

```python
def test_envsensor_peripheral_present():
    """The BME680 EnvSensor must be registered on the I2C bus."""
    assert sysbus.HasSymbol("envsensor_init")
```

### Supported Peripherals

The Renode backend is platform-agnostic. Rather than shipping one driver
template per peripheral, the generator walks the parsed model and emits a
per-peripheral assertion in `test_device.py` derived from the model's
`USE` and `CONNECT` blocks. Any peripheral in the hardware library that
the model references will produce a corresponding runtime assertion. The
generated `.repl` description uses the board's CPU and bus topology from
the Zephyr board registry (see the [Zephyr](#zephyr-rtos-zephyr) section).

### Example

```sh
demol generate renode examples/esp/esp_bme680.dev --output-dir ./renode_out
demol generate renode examples/esp/esp_bme680.dev --output-dir ./renode_out --elf-path ./build/firmware.elf
```

The first invocation writes the harness without an embedded ELF path. The
second embeds the supplied ELF path into `test_device.py` so the test
loads it directly at startup. Run the harness with:

```sh
renode --disable-xwt -e "include @renode_out/test_device.py"
```

---

## Peripheral Support Matrix

This matrix summarises driver coverage for every peripheral in the hardware
library across the five backends. A check mark (✓) means a dedicated driver
template exists; a generic placeholder (·) means the peripheral maps to a
generic GPIO / I2C / SPI / UART stub that may require user customisation;
no entry means the backend does not yet support that peripheral.

| Peripheral | RPi | RIOT | Zephyr | Wokwi | Renode |
| --- | :-: | :-: | :-: | :-: | :-: |
| `BME680` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `BME280` | ✓ | · | · | ✓ | ✓ |
| `HCSR04` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `SRF04` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `SRF05` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `HW006` | ✓ | ✓ | · | · | ✓ |
| `MPL3115A2` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `SSD1306` | ✓ | · | · | ✓ | ✓ |
| `DHT22` | ✓ | · | · | ✓ | ✓ |
| `DS18B20` | ✓ | · | · | ✓ | ✓ |
| `BH1750` | ✓ | · | · | · | ✓ |
| `MPU6050` | ✓ | · | · | · | ✓ |
| `APDS9960` | ✓ | · | · | · | ✓ |
| `PIR_HCSR501` | ✓ | · | · | ✓ | ✓ |
| `Buzzer` | ✓ | · | · | ✓ | ✓ |
| `Relay` | ✓ | · | · | ✓ | ✓ |
| `Servo` | ✓ | · | · | ✓ | ✓ |
| `LedGeneric` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `WS2812` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `TactileButton` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `TCRT5000` | ✓ | · | · | · | ✓ |
| `GPS` (uart) | ✓ | · | · | · | ✓ |
| `LIDAR` (uart) | ✓ | · | · | · | ✓ |
| `MQ2` (gas) | ✓ | · | · | · | ✓ |
| `Camera` (CSI) | ✓ | · | · | · | ✓ |
| `Speaker` / TTS | ✓ | · | · | · | ✓ |
| `MotorDriver` (PWM) | ✓ | · | · | · | ✓ |

The Renode column is topology-driven: every peripheral the model references
produces a runtime assertion. Peripherals outside the Zephyr / RIOT / Wokwi
driver sets still generate a valid `.repl` and test assertion; the firmware
itself, however, must be compiled against a backend that ships the
peripheral's driver. For new peripheral types, the recommended workflow is
to start with the RPi backend (broadest coverage) and add a Zephyr / Wokwi
driver template once the design stabilises.
