# demol/builtin_models/ — Hardware Component Library

## OVERVIEW

Pre-defined hardware models in `.hwd` format: boards, sensors, actuators, and power sources. Loaded by the DSL engine at parse time via `USE` statements.

## STRUCTURE

```
builtin_models/
├── boards/          # 13 board definitions (RPi 3/4/5, Pico, ESP32, Wemos, etc.)
├── peripherals/     # 47 sensor/actuator definitions (BME680, SRF04, SRF05, WS2812, TactileButton, PiperTTSSpeaker, etc.)
└── power/           # 2 power source definitions (Li-Ion, USB power bank)
```

## ADDING A BOARD

Create `boards/<name>.hwd`:
```
BOARD[TYPE] Name WITH
    OP
        vcc=5V, ioVcc=3V3,
        energy=<min> W, <max> W, <avg> W,
        memory.flash=<size> gb, memory.ram=<size> gb,
        cpu.family=<name>, cpu.freq=<freq> mhz
    PORTS
        spi=N, i2c=N, uart=N, gpio=N
    PINS
        power_5v[5V] @ 2,
        gnd_1[GND] @ 6,
        GPIO4[gpio,sda-1] @ 7
;
```
Board types: `RPI`, `ESP`, `ARDUINO`

## ADDING A PERIPHERAL

Create `peripherals/<name>.hwd`:
```
SENSOR[Type] Name WITH
    OP
        vcc=5V, ioVcc=3V3,
        energy=<min> mW, <max> mW, <avg> mW
    PINS
        vcc[5V] @ 1, gnd[GND] @ 5,
        sda[sda-0] @ 2, scl[scl-0] @ 3
    TEMPLATES
        raspbian="<name>.py.tmpl",
        riotos="<name>.c.tmpl"
    DEPENDENCIES
        raspbian = [{package="lib", version=">=1.0", source="pip"}]
    ATTRIBUTES
        poll_period[int] = 10
    PROPERTIES
        temperature -> "data.temperature" : int32 SCALE 100 FOR riotos
;
```
Then create matching template(s) in `templates/rpi/` and/or `templates/riot/`.

The `PROPERTIES` block is **required** for any `.hwd` whose peripheral may appear as the source of an `ALERT` on RIOT — it maps DSL property names to driver-local C expressions, declares the C type, and (for integer types stored in scaled units) the SCALE multiplier so DSL literals like `38.5 celsius` get emitted as `(int64_t)(3850)` in the generated C. Tag with `FOR riotos` to scope the property to the RIOT backend; untagged entries act as defaults.

## CONVENTIONS

- Pin functions: `gpio`, `adc`, `dac`, `pwm-N`, `sda-N`, `scl-N`, `mosi-N`, `miso-N`, `sck-N`, `cs-N`, `tx-N`, `rx-N`
- Power types: `GND`, `3V3`, `5V`, `12V`
- Energy: 3 values = min, max, avg power consumption
- Sensor types: `Env`, `Distance`, `Temperature`, `Humidity`, `Gas`, `Light`, `IMU`, `Tracker`, etc.
- Actuator types: `Led`, `NeoPixel`, `ServoController`, `MotorController`, `Relay`, `Buzzer`, etc.
- Paths resolved via `definitions.py` env vars: `BOARD_MODEL_REPO_PATH`, `PERIPHERAL_MODEL_REPO_PATH`

## ANTI-PATTERNS

- Do NOT duplicate pin numbers within a component
- Pin `ioVcc` must match the IO voltage level the component uses for data communication
- Template filenames in TEMPLATES section must match actual files in `templates/` directory — RIOT codegen is **fail-fast** on missing templates (m2t_riot.py raises `FileNotFoundError` unless `DEMOL_RIOT_SKIP_MISSING=1`)
- Declaring `riotos="..."` without a backing template is a bug — either author the template or remove the line so the .hwd is honest about its supported targets
- Dependencies use `source="pip"` or `source="apt"` — no other sources supported
