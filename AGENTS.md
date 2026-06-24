# PROJECT KNOWLEDGE BASE

**Generated:** 2026-06-23
**Commit:** e73ecef
**Branch:** feat/code_cleanup

## OVERVIEW

DeMoL (Device Modeling Language) — a textX-based Python DSL for hardware-aware IoT device modeling with automated code generation for **5 backends**: Raspberry Pi (Python), RIOT OS (C), Zephyr RTOS (C with devicetree + Kconfig), Wokwi simulator (diagram.json + wokwi.toml), and Renode emulator (.repl + pyrenode3). Also includes semantic validation (electrical safety, pin conflicts, protocol constraints), power budget analysis, SmartConnect auto-wiring, SAMPLING blocks, CONSTRAINT expressions, ALERT triggers, and a per-OS capability table (AlertValidator). (LSP/IDE integration is provided by the separate `tx-lsp` package, served via the Docker stack.)

## STRUCTURE

```
demol/                  # Core DSL package (grammar, semantics, codegen)
├── grammar/            # 4 textX grammar files (.tx)
├── lang/               # Language engine: parsing, validation, semantics
│   ├── semantics/      # Modular validator framework (33 validator classes across 15 files)
│   └── smart_connection.py  # SMARTCONNECT auto-wiring resolution (514 lines, OS-agnostic)
├── transformations/    # M2T/M2M generators: rpi, riot, zephyr, wokwi, renode, svg, docs, pinmap, smauto, json
│   ├── board_registry.py  # BoardNameRegistry: DSL board name → target-OS board name (RPi, RIOT, Zephyr, Wokwi, Renode)
│   └── docker_mixin.py    # DockerBuildMixin: shared Dockerfile + compose + install_deps generation
├── builtin_models/     # Hardware library: boards (.hwd), peripherals (.hwd), power
├── templates/          # Jinja2 templates per platform: rpi/, riot/, zephyr/, wokwi/, renode/, docs/, smauto/
└── cli/                # Click CLI: validate, generate (rpi|riot|zephyr|wokwi|renode|svg|docs|pinmap|json|smauto), analyze, fix, diff
tests/                  # pytest suite: 50+ test files + goldens/ (zephyr, wokwi, renode) + models/valid/ + models/invalid/
examples/               # Device models: rpi/ (40), esp/ (6), smauto/ (5), multi/ (3 multi-backend)
scripts/                # Automation: validation, generation, evaluation
docker/                 # Dockerfile.tests + CI container
RIOT/                   # Full RIOT OS checkout — build target for riot codegen
build/                  # Generated output (RIOT firmware projects)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add sensor/actuator type | `demol/builtin_models/peripherals/` | Create `.hwd` file, add template in `templates/rpi/` or `templates/riot/` |
| Add board | `demol/builtin_models/boards/` | `.hwd` file with BOARD[TYPE] syntax |
| Add validation rule | `demol/lang/semantics/validators/` | Inherit `BaseValidator`, see `semantics/README.md` |
| Add code generator | `demol/transformations/` | Inherit `BaseCodeGenerator` from `base_generator.py` |
| Modify grammar | `demol/grammar/*.tx` | 4 files: device, component, communication, common |
| Add CLI command | `demol/cli/cli.py` | Click framework |
| Modify visual designer | `demol-designer` repo | Separate repo: React + TypeScript + React Flow |
| Write tests | `tests/` | pytest; use `device_mm`/`component_mm` fixtures from `conftest.py` |
| Add example model | `examples/rpi/` or `examples/esp/` | `.dev` files |
| SmartConnect logic | `demol/lang/smart_connection.py` | Auto pin assignment resolution (712 lines) |
| Auto-fix engine | `demol/cli/autofix.py` | Detects and corrects common validation errors |
| Model diff engine | `demol/cli/modeldiff.py` | Semantic comparison of two `.dev` models |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `component_language` | function | `demol/__init__.py` | textX registration for `.hwd` files |
| `device_language` | function | `demol/__init__.py` | textX registration for `.dev` files |
| `get_device_mm` | function | `demol/lang/__init__.py` | Builds device metamodel with validators |
| `get_component_mm` | function | `demol/lang/__init__.py` | Builds component metamodel |
| `model_proc` | function | `demol/lang/device.py` | Model post-processing: enrichment + validation |
| `BaseCodeGenerator` | class | `demol/transformations/base_generator.py` | Abstract code generator with model querying, `OS` class constant, `_write_template` helper |
| `RPiCodeGenerator` | class | `demol/transformations/m2t_rpi.py` | Raspberry Pi Python generator (`OS = "raspbian"`) |
| `RiotCodeGenerator` | class | `demol/transformations/m2t_riot.py` | RiotOS C generator (`OS = "riotos"`) |
| `ZephyrCodeGenerator` | class | `demol/transformations/m2t_zephyr.py` | Zephyr RTOS C generator with devicetree + Kconfig (`OS = "zephyr"`) |
| `WokwiCodeGenerator` | class | `demol/transformations/m2t_wokwi.py` | Wokwi simulator generator (diagram.json + wokwi.toml, `OS = "wokwi"`) |
| `RenodeCodeGenerator` | class | `demol/transformations/m2t_renode.py` | Renode emulator generator (.repl + pyrenode3, `OS = "renode"`) |
| `BoardNameRegistry` | class | `demol/transformations/board_registry.py` | DSL board name → target-OS board name resolution |
| `DockerBuildMixin` | class | `demol/transformations/docker_mixin.py` | Shared Docker file generation for RPi/RIOT |
| `PeripheralTemplateMapper` | class | `demol/transformations/_template_mapper.py` | Generalized `get_template(peripheral_ref, os_name)` for N OSes |
| `validate_power_connection` | function | `demol/lang/semantics/validators/power.py` | Power validation (voltage compat, GND rules) |
| `ValidationReporter` | class | `demol/lang/validation.py` | Rich console validation output |
| `ValidationResult` | class | `demol/lang/validation.py` | Dataclass: status, errors, warnings, passed_rules |
| `enrich_model` | function | `demol/lang/device.py` | Resolves refs, SmartConnect, VIA routing, auto-topics |
| `demol_to_json` / `json_to_demol` | functions | `demol/transformations/json_demol.py` | Bidirectional DSL ↔ JSON conversion |

## CONVENTIONS

- **Line length**: flake8=120 (`.flake8` + Makefile both use 120), ignores E203/E501
- **Grammar files**: `.tx` extension, textX syntax. 4 modular files; `common.tx` imported by all
- **Model files**: `.dev` (device definitions), `.hwd` (hardware components)
- **Templates**: `.j2` Jinja2, named `<component>.<ext>.j2` (e.g., `bme680.py.j2`)
- **Tests**: `test_<domain>_<aspect>.py`, inline DSL strings, session-scoped fixtures
- **Validators**: Class-based (`BaseValidator` subclass), organized by category in `validators/`
- **Semantic errors**: `raise_validation_error(node, message, rule_name)` — collected, not raised immediately
- **Semantic warnings**: `raise_validation_warning(node, message, rule_name)` — for non-critical issues (IO voltage mismatch, missing GND)
- **Rule names**: `[Category-Rule]` convention (e.g., `[Conn-Power]`, `[Safety-Pin-Conflicts]`)

## ANTI-PATTERNS (THIS PROJECT)

- **NEVER** suppress semantic validation errors without `--skip-semantics` flag
- **NEVER** reuse board pins across connections (except I2C SDA/SCL and power pins which are shareable)
- **NEVER** connect GND to VCC or vice versa (PC-NO-MIX rule)
- **NEVER** use I2C addresses outside 0x00-0x7F range
- Voltage tolerance is 0.5V — connections exceeding this are errors, not warnings
- `semantics.py` (1727 lines) has been fully deleted — all validators are in `semantics/validators/`
- **NEVER** raise `TextXSemanticError` directly — use `raise_validation_error()` from `semantics/core.py`

## UNIQUE STYLES

- DSL uppercase keywords: `DEVICE`, `BOARD`, `SENSOR`, `ACTUATOR`, `CONNECT`, `SMARTCONNECT`, `POWER`, `DATA`, `USE`, `BROKER`, `NETWORK`, `SAMPLING`, `CONSTRAINT`, `ALERT`
- Pin syntax: `name[function] @ number` (e.g., `GPIO4[gpio,adc] @ 7`)
- Connection syntax: `protocol[props] board_pin -- peripheral_pin`
- `@` in CONNECT block specifies message broker topic
- `VIA BrokerName` in CONNECT routes to a specific broker (multi-broker support)
- `SMARTCONNECT Peripheral @ "topic"` — automatic pin assignment, no manual wiring
- `SAMPLING Component WITH rate = N hz, mode = continuous|on_change|batch`
- `CONSTRAINT name: expr MESSAGE "msg"` — user-defined invariants with `count()`, `sum_power()`
- `ALERT name ON Sensor WHEN cond THEN PUBLISH "topic" VIA Broker COOLDOWN N`
- Formal semantics spec in `docs/semantics.md` (mathematical notation, inference rules)

## COMMANDS

```bash
# Install
pip install -e .                    # or: make install-dev

# Validate
demol validate examples/rpi/multi_periph.dev
demol validate examples/rpi/multi_periph.dev --skip-semantics

# Generate code
demol generate rpi examples/rpi/multi_periph.dev --output-dir ./rpi_out
demol generate riot examples/esp/esp_iot_device.dev --output-dir ./build
demol generate zephyr examples/esp/esp_iot_device.dev --output-dir ./zephyr_out
demol generate zephyr examples/esp/esp_iot_device.dev --output-dir ./zephyr_out --board esp32_devkitc
demol generate wokwi examples/esp/esp_iot_device.dev --output-dir ./wokwi_out
demol generate renode examples/esp/esp_iot_device.dev --output-dir ./renode_out
demol generate svg examples/rpi/multi_periph.dev --output-dir ./diagrams
demol generate docs examples/rpi/multi_periph.dev --output-dir ./docs
demol generate pinmap examples/rpi/multi_periph.dev --output-dir ./output
demol generate json examples/rpi/multi_periph.dev --output-dir ./output
demol generate smauto examples/rpi/multi_periph.dev --output-dir ./output

# Analysis
demol analyze power examples/rpi/rpi_battery_power_analysis.dev
demol analyze power examples/rpi/rpi_battery_power_analysis.dev --json-output

# Utilities
demol fix examples/rpi/multi_periph.dev             # Auto-fix common errors
demol fix examples/rpi/multi_periph.dev --dry-run   # Preview fixes
demol diff model_a.dev model_b.dev                  # Semantic diff
demol diff model_a.dev model_b.dev --json-output

# Test
make test                           # pytest tests/
make test-local                     # pytest + validation + transformations
make test-cov                       # with coverage

# Quality
make lint                           # flake8
make format                         # black
make type-check                     # mypy

# Docker
make docker-test                    # Tests in container
```

## NOTES

- `RIOT/` is a full OS checkout (~40k files) — exclude from searches/analysis
- `build/` contains generated output — do not edit manually
- `venv/` and `.venv/` are virtual environments — exclude from searches
- `demol/lang/semantics.py` has been fully deleted — all validators are in `semantics/validators/`
- Build: `pyproject.toml` only (PEP 517/518); `setup.py` and `setup.cfg` removed (commit e6985fb)
- Visual designer is in the separate `demol-designer` repo
- `demol/definitions.py` paths use `os.getenv()` for overridable model repos (DEVICES_MODEL_REPO_PATH)
- 50+ test files covering ~790 test cases; CI runs across Python 3.9–3.13 matrix
- `demol/lang/smart_connection.py` (514 lines) handles SMARTCONNECT auto-wiring resolution (verified OS-agnostic)
- RIOT mapper is **fail-fast on missing templates** — set `DEMOL_RIOT_SKIP_MISSING=1` only if intentional skipping is required
- RIOT codegen ships **8 driver pairs** (bme680, hw006, mpl3115a2, srf04, srf05, led, ws281x, button); CI matrix compiles 3 ESP examples per push (wemos_bme680, wemos_button, wemos_srf05)
- Zephyr codegen mirrors the RIOT set with **8 driver templates** + shared `trigger_echo_init`/`trigger_echo_read` macros for ultrasonic sensors (hcsr04, srf04, srf05); hcsr04p stays RIOT-only, hw006 is IR proximity (no trigger-echo macro); uses Zephyr modern devicetree API (`DEVICE_DT_GET`, `gpio_dt_spec`, `sensor_sample_fetch`)
- `OperatingSystem` enum: `raspbian`, `riotos`, `zephyr`, `arduino`, `esp-idf`, `esp-idf-rtos` (freertos removed as phantom value)
- `BoardNameRegistry` resolves DSL board names to target-OS board names across RPi (raspbian), RIOT, Zephyr, and Wokwi
- `PeripheralTemplateMapper` is now `get_template(peripheral_ref, os_name)` — single API for N OSes via the new `tpl_<os>` map in `.hwd` files
- `DockerBuildMixin` consolidates Dockerfile + compose + install_deps generation; mixed into RPiCodeGenerator and RiotCodeGenerator
- `AlertValidator` uses a `PER_OS_CAPABILITIES` dict (e.g. `riotos: {multi_broker: False}`) replacing the prior RIOT-specific check
- Golden-file testing via `syrupy==5.1.0` for all 3 new backends (Zephyr, Wokwi, Renode); goldens live in `tests/goldens/{zephyr,wokwi,renode}/`
- CI: `.github/workflows/zephyr-build.yml` runs `west build -b native_sim` for 5 ESP examples (matrix strategy, ubuntu-latest)
- Zephyr value added to `OperatingSystem` enum (was `freertos`); backward compat preserved by keeping rule name `[Safety-Alert-RiotMultiBroker]`
- `OperationalPeripheral` simplified: removed dead `riotTpl`/`piTpl` keys (the canonical path was already `TEMPLATES raspbian=... riotos=...` via `TemplateMapping`)
- 3 new multi-backend example devices in `examples/multi/`: `simple_sensor.dev`, `actuator_switch.dev`, `iot_mqtt.dev` (each generates for all 5 backends)
- New documentation: `docs/backends.md` (per-backend reference), `examples/README.md` (example gallery)
