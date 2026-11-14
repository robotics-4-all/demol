# Verifying generated Raspberry Pi code

`demol generate rpi` emits Python nodes that read sensors and publish to an MQTT
broker. Verifying that output has four levels. Levels 1–3 run on any x86 Linux
host; level 4 needs a real Raspberry Pi.

| Level | Question answered | Needs | Command |
|-------|-------------------|-------|---------|
| L1 | Does the generated tree import cleanly as flat, script-launched code? | nothing | `pytest tests/test_rpi_generated_imports.py` |
| L2 | Do readings reach the configured broker with the right topic and payload? | Docker | `make test-rpi-e2e` (runs L1+L2+L3) |
| L3 | Does driver code map hardware fields correctly? | nothing (vendor SDKs are emulated) | `DEMOL_RUN_INTEGRATION=1 pytest tests/integration/test_rpi_driver_emulation.py` |
| L4 | Does it work on a real Pi 3/4 with real sensors? | Pi + Docker + broker | `make test-rpi-hil MODEL=... BROKER_HOST=... TOPIC=...` |

Integration tests are opt-in; set `DEMOL_RUN_INTEGRATION=1` (the `make`
targets do this) so the default `pytest` run stays offline. When the variable is
set, a missing or unusable Docker is a **failure**, not a skip — a green run
always means the broker tests really executed.

## L1 — generated tree imports

Generates every `examples/rpi/*.dev` model plus Pi 3 and Pi 4 variants and
imports every emitted module in a subprocess, stubbing hardware-only third-party
libraries on demand. This catches missing generated modules (`peripheral.py`),
package-relative imports in a flat script layout, and message classes that are
referenced but never emitted.

L1 imports modules; it does not instantiate drivers or open a broker connection.
Runtime behaviour is L2's job. The stub layer satisfies any `ModuleNotFoundError`,
so L1 cannot detect a misspelled vendor import — only a broken module graph.

## L2 — broker contract

For each scenario the test generates a model whose broker points at an ephemeral
Eclipse Mosquitto container, replaces the generated driver with a deterministic
fake, runs the node as a script, and asserts what a subscriber observes:

- continuous sampling: topic, payload fields, header timestamp, ordering
- `on_change`: publish only when the threshold is crossed
- `batch`: complete buffers only
- `ALERT ... THEN PUBLISH`: alert topic and payload
- actuator nodes: inbound command reaches the driver
- payloads are JSON objects

Run with:

```bash
make test-rpi-e2e
```

L2 proves the publish path, message schema and wire topic. It does not prove a
physical sensor produces those values — that is L4.

## L3 — driver emulation

Imports the generated driver, replaces the vendor SDK (`bme680`,
`adafruit_ina219`, `adafruit_ads1x15`) with deterministic stand-ins, and checks
the field mapping produced by `read()`. This validates codegen logic, not the
vendor library.

Kernel-level I2C emulation is available as a separate probe for real `smbus2`
reads:

```bash
sudo ./scripts/rpi_i2c_stub_check.sh 0x76 0xd0 0x61
```

It loads the `i2c-stub` kernel module, seeds one register, reads it back through
`smbus2`, and unloads the module only if the script loaded it. This is a
proof-of-concept for the bus, not a driver test: generated drivers pin I2C bus 1,
so a full driver run needs a stub adapter numbered 1 or a shim that selects the
stub bus.

## Why not a full-system emulator?

- **QEMU `raspi3b`/`raspi4b`** boots a Linux kernel but models almost none of the
  I2C/SPI/1-Wire sensor peripherals, and running Docker inside it is impractical.
  Booting an entire Pi image to test one node is far slower than L2 and still
  cannot answer "did the sensor value reach the broker?" without extra shims.
- **Renode** (already a DeMoL backend) targets bare-metal firmware such as the
  ESP32 flows, not Raspberry Pi OS userland Python.
- **Wokwi** supports ESP32/Pico, not Raspberry Pi 3/4 Linux.

A full-system emulator would add a lot of runtime for coverage that L2 (message
path) and L3 (field mapping) already provide on x86. Real Pi behaviour is L4.

## L4 — hardware-in-the-loop

Run on the Pi that will host the device:

```bash
make test-rpi-hil \
  MODEL=examples/rpi/multi_periph.dev \
  BROKER_HOST=192.168.1.10 \
  BROKER_PORT=1883 \
  TOPIC=sensors/environment
```

The script generates code into a temp directory, `docker compose up -d --build`s
it, subscribes with `mosquitto_sub`, and fails if fewer than 5 messages arrive
within 30 seconds. On failure it prints container status and logs. Use
`--expect`, `--timeout`, `--keep` and `--output-dir` for control. A temp
directory is deleted on exit; a user-supplied `--output-dir` is left in place.

This is the only level that validates `privileged: true`, `/dev/i2c-1`,
`/dev/gpiomem`, wiring, and real driver/kernel behavior. `BROKER_HOST` only
points the subscriber at the broker: the model's own `BROKER[MQTT]` block must
already name a host the Pi can reach, otherwise the run ends with zero messages.

## Notes and limitations

- L2 uses fake drivers by design: it isolates the messaging path from hardware.
- Broker credentials are compiled into the node source. Generated files are
  written with mode `0600`, and the node reads `DEMOL_BROKER_USERNAME` /
  `DEMOL_BROKER_PASSWORD` from the environment first, so a deployment can
  override them without regenerating code.
- `l298n`, `a4988`, `nrf24l01` and `ssd1306` implement `write(msg)` so actuator
  nodes can dispatch commands; add the same method to any future actuator driver.
- Broker/topic/credential strings are rendered with `tojson`, so a quote or
  newline in a `.dev` model cannot break out of its Python literal.
- `eclipse-mosquitto:2.0.20` is pulled on first run; pre-pull it on CI hosts.
- Only `bme680`, `ina219` and `ads1115` have driver-level field-mapping coverage.
  Other peripherals are covered by L1 (importability) and by the message-class
  schema in `msg.py`, not by a broker round-trip.
- Message classes are a static schema. If a driver's `read()` emits a key the
  class does not declare, pydantic drops it silently and the field never reaches
  the broker. L3 catches this only for the three covered drivers; extend the L3
  stub list when touching a new driver.
- `ALERT ... THEN ACTIVATE` publishes an informational payload
  (`{"command": "activate", "source": ...}`); generated actuator nodes subscribe
  with their own message schema and therefore ignore it. Use
  `ALERT ... THEN PUBLISH` for actions that must reach a device.
