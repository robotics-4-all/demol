# demol/transformations/ — Code Generators

## OVERVIEW

Model-to-Text (M2T) and Model-to-Model (M2M) transformations. Generates platform-specific code, diagrams, documentation, and serialization formats from parsed device models.

## STRUCTURE

```
transformations/
├── base_generator.py          # Abstract base: model querying, pin extraction, attribute conversion (631 lines)
├── m2t_rpi.py                 # RPiCodeGenerator → Python code (RPi.GPIO, smbus2, spidev) (371 lines)
├── m2t_riot.py                # RiotCodeGenerator → C code for RIOT OS (290 lines)
├── m2t_docs.py                # Documentation generator → Markdown hardware guide
├── m2t_pinmap.py              # Pin mapping report → Markdown + JSON (266 lines)
├── device_to_svg.py           # Wiring diagram → SVG (282 lines)
├── infrastructure_to_svg.py   # Infrastructure diagram → SVG (Edge/Comm/App layers) (143 lines)
├── json_demol.py              # Bidirectional DSL ↔ JSON conversion (509 lines)
├── m2m_smauto.py              # M2M → SmartAuto DSL format (129 lines)
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
| `BaseCodeGenerator` | class | 631 | Abstract base: `get_broker_config()`, `get_board()`, `get_connections()`, pin extraction |
| `RPiCodeGenerator` | class | 371 | Generates Python + Dockerfile + docker-compose + requirements.txt + install_deps.sh |
| `RiotCodeGenerator` | class | 290 | Generates C + Makefile + build_docker.sh for RIOT OS |
| `demol_to_json` | function | 509 | Serialize parsed model to JSON dict |
| `json_to_demol` | function | — | Generate `.dev` DSL string from JSON dict |

## CONVENTIONS

- Generators inherit `BaseCodeGenerator` and call `self.setup_template_environment()` for Jinja2
- Templates live in `demol/templates/<platform>/` — named `<component>.<ext>.j2`
- Pin extraction methods: `_extract_gpio_pins()`, `_extract_i2c_pins()`, `_extract_spi_pins()`, `_extract_uart_pins()`, `_extract_pwm_pins()`
- RPi generator produces deployment artifacts alongside code (Dockerfile, docker-compose, etc.)
- RiotOS generator produces a complete RIOT application directory with Makefile referencing `$(RIOTBASE)`

## ANTI-PATTERNS

- Do NOT bypass `BaseCodeGenerator` — all generators must use its model querying methods
- Do NOT hardcode template paths — use `demol/definitions.py` constants (`TEMPLATES_RPI`, `TEMPLATES`, `TEMPLATES_DOCS`)
- Template files must match peripheral `.hwd` TEMPLATES section (e.g., `raspbian="bme680.py.tmpl"`)
