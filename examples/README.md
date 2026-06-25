# Example Gallery

DeMoL ships with a curated set of `.dev` models that exercise every language
construct, peripheral, and backend in the toolchain. The gallery is
organised by example directory: each directory groups models that share a
target board family and operating system. The table below each section
lists every `.dev` file in that directory and indicates which of the five
code-generation backends (RPi, RIOT, Zephyr, Wokwi, Renode) the model
supports. A check mark (✓) means the model compiles to a runnable artifact
on that backend; an em-dash (—) means that backend is not applicable given
the model's `os=` declaration and board choice.

The example inventory is the cross-backend test corpus: every model here
is exercised by `demol generate` on at least one backend in CI, and the
[cross-backend integration test](tests/) round-trips a model through the
full pipeline (parse → validate → generate) on every applicable backend.

## How to Use

Pick an example that matches your target board and run any of the supported
backends against it:

```sh
demol validate <example.dev>
demol generate rpi   <example.dev> --output-dir ./rpi_out
demol generate riot  <example.dev> --output-dir ./riot_out
demol generate zephyr <example.dev> --output-dir ./zephyr_out
demol generate wokwi  <example.dev> --output-dir ./wokwi_out
demol generate renode <example.dev> --output-dir ./renode_out
```

The full reference for every backend (CLI flags, output structure,
peripheral support) lives in [`docs/backends.md`](../docs/backends.md).

## Example Directories

| Directory | Target | Models | Primary backends |
| --- | --- | --- | --- |
| [`examples/rpi/`](#raspberry-pi-examples) | Raspberry Pi on Raspbian | 40 | RPi, Wokwi |
| [`examples/esp/`](#esp-examples) | ESP32 / WemosD1Mini on RIOT or Zephyr | 7 | RIOT, Zephyr, Wokwi, Renode |
| [`examples/smauto/`](#smauto-examples) | Raspberry Pi → SmartAuto automation | 5 | RPi, Wokwi |

Total: 52 `.dev` models across three example directories.

---

## Raspberry Pi Examples

`examples/rpi/*.dev` — 40 models targeting Raspberry Pi boards running
Raspbian. Every model in this directory uses a Raspberry Pi 4B or 5
board, so it compiles to RPi Python code and maps cleanly to the Wokwi
`board-raspberry-pi-4b` / `board-raspberry-pi-5` simulator parts.

| Example | RPi | RIOT | Zephyr | Wokwi | Renode |
| --- | :-: | :-: | :-: | :-: | :-: |
| [`multi_periph.dev`](../examples/rpi/multi_periph.dev) | ✓ | — | — | ✓ | — |
| [`RPi_ADC.dev`](../examples/rpi/RPi_ADC.dev) | ✓ | — | — | ✓ | — |
| [`rpi_5_TCRT.dev`](../examples/rpi/rpi_5_TCRT.dev) | ✓ | — | — | ✓ | — |
| [`rpi5_ToF.dev`](../examples/rpi/rpi5_ToF.dev) | ✓ | — | — | ✓ | — |
| [`rpi_access_control.dev`](../examples/rpi/rpi_access_control.dev) | ✓ | — | — | ✓ | — |
| [`rpi_alert_triggers.dev`](../examples/rpi/rpi_alert_triggers.dev) | ✓ | — | — | ✓ | — |
| [`rpi_all_features.dev`](../examples/rpi/rpi_all_features.dev) | ✓ | — | — | ✓ | — |
| [`rpi_apds9960_gesture.dev`](../examples/rpi/rpi_apds9960_gesture.dev) | ✓ | — | — | ✓ | — |
| [`rpi_battery_power_analysis.dev`](../examples/rpi/rpi_battery_power_analysis.dev) | ✓ | — | — | ✓ | — |
| [`rpi_bh1750_lux.dev`](../examples/rpi/rpi_bh1750_lux.dev) | ✓ | — | — | ✓ | — |
| [`rpi_camera_pan_tilt.dev`](../examples/rpi/rpi_camera_pan_tilt.dev) | ✓ | — | — | ✓ | — |
| [`rpi_constraint_bme.dev`](../examples/rpi/rpi_constraint_bme.dev) | ✓ | — | — | ✓ | — |
| [`rpi_constraints_demo.dev`](../examples/rpi/rpi_constraints_demo.dev) | ✓ | — | — | ✓ | — |
| [`rpi_dht22_climate.dev`](../examples/rpi/rpi_dht22_climate.dev) | ✓ | — | — | ✓ | — |
| [`rpi_ds18b20_thermometer.dev`](../examples/rpi/rpi_ds18b20_thermometer.dev) | ✓ | — | — | ✓ | — |
| [`rpi_env_station.dev`](../examples/rpi/rpi_env_station.dev) | ✓ | — | — | ✓ | — |
| [`RPi_gas_led.dev`](../examples/rpi/RPi_gas_led.dev) | ✓ | — | — | ✓ | — |
| [`rpi_gps_compass.dev`](../examples/rpi/rpi_gps_compass.dev) | ✓ | — | — | ✓ | — |
| [`rpi_greenhouse_sampling.dev`](../examples/rpi/rpi_greenhouse_sampling.dev) | ✓ | — | — | ✓ | — |
| [`rpi_health_monitor.dev`](../examples/rpi/rpi_health_monitor.dev) | ✓ | — | — | ✓ | — |
| [`rpi_hw006_proximity.dev`](../examples/rpi/rpi_hw006_proximity.dev) | ✓ | — | — | ✓ | — |
| [`rpi_iot_device.dev`](../examples/rpi/rpi_iot_device.dev) | ✓ | — | — | ✓ | — |
| [`rpi_mixed_connect.dev`](../examples/rpi/rpi_mixed_connect.dev) | ✓ | — | — | ✓ | — |
| [`rpi_motor_lab.dev`](../examples/rpi/rpi_motor_lab.dev) | ✓ | — | — | ✓ | — |
| [`rpi_mpu6050_imu.dev`](../examples/rpi/rpi_mpu6050_imu.dev) | ✓ | — | — | ✓ | — |
| [`rpi_mq2_gas_alarm.dev`](../examples/rpi/rpi_mq2_gas_alarm.dev) | ✓ | — | — | ✓ | — |
| [`rpi_multi_broker_via.dev`](../examples/rpi/rpi_multi_broker_via.dev) | ✓ | — | — | ✓ | — |
| [`rpi_piper_tts.dev`](../examples/rpi/rpi_piper_tts.dev) | ✓ | — | — | ✓ | — |
| [`rpi_pir_motion.dev`](../examples/rpi/rpi_pir_motion.dev) | ✓ | — | — | ✓ | — |
| [`rpi_precision_scale.dev`](../examples/rpi/rpi_precision_scale.dev) | ✓ | — | — | ✓ | — |
| [`rpi_relay_switch.dev`](../examples/rpi/rpi_relay_switch.dev) | ✓ | — | — | ✓ | — |
| [`rpi_robot.dev`](../examples/rpi/rpi_robot.dev) | ✓ | — | — | ✓ | — |
| [`rpi_smart_connect.dev`](../examples/rpi/rpi_smart_connect.dev) | ✓ | — | — | ✓ | — |
| [`rpi_smart_home.dev`](../examples/rpi/rpi_smart_home.dev) | ✓ | — | — | ✓ | — |
| [`rpi_soil_moisture_garden.dev`](../examples/rpi/rpi_soil_moisture_garden.dev) | ✓ | — | — | ✓ | — |
| [`rpi_srf04_battery.dev`](../examples/rpi/rpi_srf04_battery.dev) | ✓ | — | — | ✓ | — |
| [`rpi_uart_lidar.dev`](../examples/rpi/rpi_uart_lidar.dev) | ✓ | — | — | ✓ | — |
| [`rpi_weather_station_v1.dev`](../examples/rpi/rpi_weather_station_v1.dev) | ✓ | — | — | ✓ | — |
| [`rpi_weather_station_v2.dev`](../examples/rpi/rpi_weather_station_v2.dev) | ✓ | — | — | ✓ | — |
| [`rpi_wireless_sensor_node.dev`](../examples/rpi/rpi_wireless_sensor_node.dev) | ✓ | — | — | ✓ | — |

### Quick start

```sh
demol generate rpi examples/rpi/multi_periph.dev --output-dir ./out
demol generate wokwi examples/rpi/multi_periph.dev --output-dir ./out
```

The RPi generator produces a complete Python application with commlib-py
messaging, MQTT publishing, and a Docker deployment manifest. The Wokwi
generator produces a `diagram.json` that loads the same circuit in the
[Wokwi simulator](https://wokwi.com/) for interactive testing.

---

## ESP Examples

`examples/esp/*.dev` — 7 models targeting ESP32 (`ESP32Wroom32`) and
WemosD1Mini boards. These models are the cross-backend test corpus: each
one is designed to compile to RIOT C, Zephyr C, Wokwi JSON, and a Renode
`.repl` platform description from the same `.dev` source. The CI matrix
compiles the ESP examples on all three microcontroller backends per push.

| Example | RPi | RIOT | Zephyr | Wokwi | Renode |
| --- | :-: | :-: | :-: | :-: | :-: |
| [`esp_bme680.dev`](../examples/esp/esp_bme680.dev) | — | ✓ | ✓ | ✓ | ✓ |
| [`esp_iot_device.dev`](../examples/esp/esp_iot_device.dev) | — | ✓ | ✓ | ✓ | ✓ |
| [`wemos_a.dev`](../examples/esp/wemos_a.dev) | — | ✓ | ✓ | ✓ | ✓ |
| [`wemos_bme680.dev`](../examples/esp/wemos_bme680.dev) | — | ✓ | ✓ | ✓ | ✓ |
| [`wemos_bme680_alert.dev`](../examples/esp/wemos_bme680_alert.dev) | — | ✓ | ✓ | ✓ | ✓ |
| [`wemos_button.dev`](../examples/esp/wemos_button.dev) | — | ✓ | ✓ | ✓ | ✓ |
| [`wemos_srf05.dev`](../examples/esp/wemos_srf05.dev) | — | ✓ | ✓ | ✓ | ✓ |

### Quick start

```sh
demol generate zephyr examples/esp/esp_bme680.dev --output-dir ./zephyr_out
demol generate renode  examples/esp/esp_bme680.dev --output-dir ./renode_out
demol generate wokwi   examples/esp/esp_bme680.dev --output-dir ./wokwi_out
```

The Zephyr generator writes a complete Zephyr application skeleton with
devicetree overlay, `prj.conf`, and one driver source file per peripheral.
The Renode generator writes a `.repl` platform description and a
`pyrenode3` test script that boots the simulation and asserts that each
declared peripheral is present at runtime. The Wokwi generator writes a
`diagram.json` ready for the Wokwi simulator.

To run the Renode test against a real firmware build:

```sh
demol generate renode examples/esp/esp_bme680.dev \
    --output-dir ./renode_out --elf-path ./build/firmware.elf
renode --disable-xwt -e "include @renode_out/test_device.py"
```

---

## SMAuto Examples

`examples/smauto/*.dev` — 5 models that target Raspberry Pi boards and
demonstrate the `m2m_smauto` model-to-model transformation to the SmartAuto
automation DSL. These models are RPi-only at the firmware level (same as
the `examples/rpi/` set) but additionally produce a SmartAuto automation
model that integrates with the SmartAuto runtime.

| Example | RPi | RIOT | Zephyr | Wokwi | Renode |
| --- | :-: | :-: | :-: | :-: | :-: |
| [`EntranceLEDs.dev`](../examples/smauto/EntranceLEDs.dev) | ✓ | — | — | ✓ | — |
| [`ParkingLeds.dev`](../examples/smauto/ParkingLeds.dev) | ✓ | — | — | ✓ | — |
| [`ParkingSensor.dev`](../examples/smauto/ParkingSensor.dev) | ✓ | — | — | ✓ | — |
| [`RPiFan.dev`](../examples/smauto/RPiFan.dev) | ✓ | — | — | ✓ | — |
| [`SmartWindow.dev`](../examples/smauto/SmartWindow.dev) | ✓ | — | — | ✓ | — |

### Quick start

```sh
demol generate rpi    examples/smauto/ParkingSensor.dev --output-dir ./rpi_out
demol generate smauto examples/smauto/ParkingSensor.dev --output-dir ./smauto_out
```

The `rpi` subcommand produces a runnable Python application for the
Raspberry Pi. The `smauto` subcommand runs the M2M transformation that
emits a SmartAuto automation model from the same source. Both generators
read the same validated `.dev` file, so the firmware and the automation
model stay in lockstep as the design evolves.
