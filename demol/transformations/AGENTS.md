# demol/transformations/ — Code Generators

## OVERVIEW

Model-to-Text (M2T) and Model-to-Model (M2M) transformations. Generates platform-specific code, diagrams, documentation, and serialization formats from parsed device models.

## STRUCTURE

```
transformations/
├── base_generator.py          # Abstract base: model querying, pin extraction, attribute conversion (631 lines)
├── m2t_rpi.py                 # RPiCodeGenerator → Python code (RPi.GPIO, smbus2, spidev) (332 lines)
├── m2t_riot.py                # RiotCodeGenerator → C code for RIOT OS
├── m2t_docs.py                # Documentation generator → Markdown hardware guide
├── m2t_pinmap.py              # Pin mapping report → Markdown + JSON
├── device_to_svg.py           # Wiring diagram → SVG
├── infrastructure_to_svg.py   # Infrastructure diagram → SVG (Edge/Comm/App layers)
├── json_demol.py              # Bidirectional DSL ↔ JSON conversion (509 lines)
├── m2m_smauto.py              # M2M → SmartAuto DSL format
└── __init__.py
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add new platform generator | Create new file | Inherit `BaseCodeGenerator`, implement `generate()` |
| Modify RPi output | `m2t_rpi.py` + `../templates/rpi/` | Generator selects templates; templates contain Jinja2 |
| Modify RiotOS output | `m2t_riot.py` + `../templates/riot/` | Same pattern |
| Add diagram type | `device_to_svg.py` or new file | SVG generation is template-free (programmatic) |
| JSON serialization | `json_demol.py` | `demol_to_json()` / `json_to_demol()` |
| Pin mapping report | `m2t_pinmap.py` | Generates MD + JSON pin assignment reports |

## CODE MAP

| Symbol | Type | Lines | Role |
|--------|------|-------|------|
| `BaseCodeGenerator` | class | 631 | Abstract base: `get_broker_config()`, `get_board()`, `get_connections()`, pin extraction, ALERT helpers (`get_alerts_for_source`, `resolve_broker`, `cooldown_to_seconds`, `resolve_activate_target_topic`, `get_alert_property_resolver`, `render_riot_condition`, `render_riot_comparison`) |
| `RPiCodeGenerator` | class | 332 | Generates Python + Dockerfile + docker-compose + requirements.txt + install_deps.sh |
| `RiotCodeGenerator` | class | — | Generates C + Makefile + build_docker.sh + Dockerfile.riotbuild for self-contained RIOT builds |
| `demol_to_json` | function | 509 | Serialize parsed model to JSON dict |
| `json_to_demol` | function | — | Generate `.dev` DSL string from JSON dict |

## CONVENTIONS

- Generators inherit `BaseCodeGenerator` and call `self.setup_template_environment()` for Jinja2
- Templates live in `demol/templates/<platform>/` — named `<component>.<ext>.j2`
- Pin extraction methods: `_extract_gpio_pins()`, `_extract_i2c_pins()`, `_extract_spi_pins()`, `_extract_uart_pins()`, `_extract_pwm_pins()`
- RPi generator produces deployment artifacts alongside code (Dockerfile, docker-compose, etc.)
- RiotOS generator produces a complete RIOT application directory with Makefile referencing `$(RIOTBASE)`, plus `Dockerfile.riotbuild` and `build_docker.sh` so end users only need Docker (the script auto-builds `demol/riotbuild:<version>` if missing, cloning RIOT inside the image)
- RIOT version/repo are env-overridable via `DEMOL_RIOT_VERSION` and `DEMOL_RIOT_REPO` at generation time
- ALERT codegen (both platforms): per-source AlertTrigger evaluators with cooldown gates. RPi emits `alerts.py` runtime + per-driver `_build_alerts()` closures. RIOT emits inline per-driver `static uint64_t last_fire_<name>` + `if (condition_c) { … publish_alert(payload, topic); }` blocks via `_build_riot_alert_context()`. RIOT alerts route through the `publish_alert()` wrapper in `main.c` (single-MQTTClient constraint); non-default `VIA` brokers are downgraded with a logger warning + the `[Safety-Alert-RiotMultiBroker]` validator warning.
- RIOT condition rendering uses the `.hwd` `PROPERTIES` block (DSL property → C expression + type + SCALE) — see `get_alert_property_resolver()` in `base_generator.py`

## ANTI-PATTERNS

- Do NOT bypass `BaseCodeGenerator` — all generators must use its model querying methods
- Do NOT hardcode template paths — use `demol/definitions.py` constants (`TEMPLATES_RPI`, `TEMPLATES`, `TEMPLATES_DOCS`)
- Template files must match peripheral `.hwd` TEMPLATES section (e.g., `raspbian="bme680.py.tmpl"`)
