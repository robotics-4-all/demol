# demol/transformations/ — Code Generators

## OVERVIEW

Model-to-Text (M2T) and Model-to-Model (M2M) transformations. Generates platform-specific code, diagrams, documentation, and serialization formats from parsed device models.

## STRUCTURE

```
transformations/
├── base_generator.py          # Abstract base: model querying, pin extraction, attribute conversion
├── m2t_rpi.py                 # RPiCodeGenerator → Python code (RPi.GPIO, smbus2, spidev)
├── m2t_riot.py                # RiotCodeGenerator → C code for RIOT OS
├── m2t_zephyr.py              # ZephyrCodeGenerator → C code + devicetree + Kconfig for Zephyr RTOS
├── m2t_wokwi.py               # WokwiCodeGenerator → diagram.json + wokwi.toml for Wokwi simulator
├── m2t_renode.py              # RenodeCodeGenerator → .repl + pyrenode3 for Renode emulator
├── m2t_docs.py                # Documentation generator → Markdown hardware guide
├── m2t_pinmap.py              # Pin mapping report → Markdown + JSON
├── device_to_svg.py           # Wiring diagram → SVG
├── infrastructure_to_svg.py   # Infrastructure diagram → SVG (Edge/Comm/App layers)
├── json_demol.py              # Bidirectional DSL ↔ JSON conversion
├── m2m_smauto.py              # M2M → SmartAuto DSL format
├── board_registry.py          # BoardNameRegistry: DSL board → target-OS board name
├── docker_mixin.py            # DockerBuildMixin: shared Dockerfile + compose + install_deps generation
├── _template_mapper.py        # PeripheralTemplateMapper: get_template() for N OSes
└── __init__.py
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add new platform generator | Create new file | Inherit `BaseCodeGenerator`, implement `generate()` |
| Modify RPi output | `m2t_rpi.py` + `../templates/rpi/` | Generator selects templates; templates contain Jinja2 |
| Modify RIOT output | `m2t_riot.py` + `../templates/riot/` | Same pattern |
| Modify Zephyr output | `m2t_zephyr.py` + `../templates/zephyr/` | Same pattern; emits CMakeLists.txt, prj.conf, devicetree overlay |
| Modify Wokwi output | `m2t_wokwi.py` + `../templates/wokwi/` | Emits diagram.json + wokwi.toml |
| Modify Renode output | `m2t_renode.py` + `../templates/renode/` | Emits .repl + pyrenode3 test script |
| Add diagram type | `device_to_svg.py` or new file | SVG generation is template-free (programmatic) |
| JSON serialization | `json_demol.py` | `demol_to_json()` / `json_to_demol()` |
| Pin mapping report | `m2t_pinmap.py` | Generates MD + JSON pin assignment reports |
| Board name mapping | `board_registry.py` | `BoardNameRegistry`: DSL board name → target-OS board name |
| Docker deployment | `docker_mixin.py` | `DockerBuildMixin`: shared Dockerfile + compose + install_deps |
| Template resolution | `_template_mapper.py` | `get_template(peripheral_ref, os_name)` for N OSes |

## CODE MAP

| Symbol | Type | Role |
|--------|------|------|
| `BaseCodeGenerator` | class | Abstract base: model querying, pin extraction, ALERT helpers, CONSTRAINT helpers (`_generate_constraint_header`, `_generate_constraint_source`), broker config |
| `RPiCodeGenerator` | class | Generates Python + Dockerfile + docker-compose + requirements.txt + install_deps.sh. Full AMQP/Redis broker support |
| `RiotCodeGenerator` | class | Generates C + Makefile + build_docker.sh + Dockerfile.riotbuild. CONSTRAINT and broker stubs |
| `ZephyrCodeGenerator` | class | Generates C + CMakeLists.txt + prj.conf + devicetree overlay + Kconfig. CONSTRAINT and broker stubs |
| `WokwiCodeGenerator` | class | Generates diagram.json + wokwi.toml for Wokwi simulator |
| `RenodeCodeGenerator` | class | Generates .repl + pyrenode3 test script for Renode emulator |
| `BoardNameRegistry` | class | Resolves DSL board names to target-OS board names (RPi, RIOT, Zephyr, Wokwi) |
| `DockerBuildMixin` | class | Shared Dockerfile + docker-compose + install_deps generation for RPi and RIOT |
| `PeripheralTemplateMapper` | class | `get_template(peripheral_ref, os_name)` for N OSes via `.hwd` TEMPLATES section |
| `demol_to_json` | function | Serialize parsed model to JSON dict |
| `json_to_demol` | function | Generate `.dev` DSL string from JSON dict |

## CONVENTIONS

- Generators inherit `BaseCodeGenerator` and call `self.setup_template_environment()` for Jinja2
- Templates live in `demol/templates/<platform>/` — named `<component>.<ext>.j2`
- Pin extraction methods: `_extract_gpio_pins()`, `_extract_i2c_pins()`, `_extract_spi_pins()`, `_extract_uart_pins()`, `_extract_pwm_pins()`
- RPi generator produces deployment artifacts alongside code (Dockerfile, docker-compose, etc.)
- RIOT generator produces a complete RIOT application directory with Makefile referencing `$(RIOTBASE)`, plus `Dockerfile.riotbuild` and `build_docker.sh`
- Zephyr generator produces a complete Zephyr application: CMakeLists.txt, prj.conf, devicetree overlay, static main.c, and one driver source file per peripheral
- Wokwi generator produces diagram.json + wokwi.toml for the Wokwi web simulator
- Renode generator produces .repl platform description + pyrenode3 test script
- RIOT version/repo are env-overridable via `DEMOL_RIOT_VERSION` and `DEMOL_RIOT_REPO` at generation time
- CONSTRAINT codegen: RPi emits `constraints.py` runtime, RIOT emits `constraint.c`/`constraint.h`, Zephyr emits `constraint.c`/`constraint.h`
- Broker support: RPi has full AMQP (pika) and Redis (redis-py) support; RIOT and Zephyr emit stubs with TODO markers
- ALERT codegen (all platforms): per-source AlertTrigger evaluators with cooldown gates. RPi emits `alerts.py` runtime + per-driver `_build_alerts()` closures. RIOT/Zephyr emit inline per-driver static blocks with cooldown checks
- RIOT condition rendering uses the `.hwd` `PROPERTIES` block (DSL property → C expression + type + SCALE) — see `get_alert_property_resolver()` in `base_generator.py`
- BoardNameRegistry resolves DSL board names to target-OS board names across all 5 backends
- PeripheralTemplateMapper adds `sensor_`/`actuator_` prefix from `.hwd` TEMPLATES section

## ANTI-PATTERNS

- Do NOT bypass `BaseCodeGenerator` — all generators must use its model querying methods
- Do NOT hardcode template paths — use `demol/definitions.py` constants (`TEMPLATES_RPI`, `TEMPLATES`, `TEMPLATES_DOCS`)
- Template files must match peripheral `.hwd` TEMPLATES section (e.g., `raspbian="bme680.py.tmpl"`)
- Do NOT skip template rendering for peripherals with no matching `.hwd` TEMPLATES entry — log a warning and continue
- Do NOT mix board names across backends — use `BoardNameRegistry` for cross-platform board resolution
