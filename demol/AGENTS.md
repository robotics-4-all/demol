# demol/ — Core DSL Package

## OVERVIEW

textX-based DSL engine: grammar → metamodel → parsing → validation → code generation.

## STRUCTURE

```
demol/
├── __init__.py          # textX language registration (@language decorators)
├── definitions.py       # Path constants, env-overridable model repo paths
├── utils.py             # Shared utilities (246 lines)
├── grammar/             # 4 textX grammar files defining DSL syntax
├── lang/                # Language engine: metamodels, validation, semantics
├── transformations/     # Code generators: RPi, RiotOS, SVG, docs, JSON, SmAuto
├── builtin_models/      # Hardware library: boards, peripherals, power sources
├── templates/           # Jinja2 templates per platform
├── cli/                 # Click CLI (cli.py → `demol` command)
└── api/                 # Internal API helpers (not the top-level api/)
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| textX language registration | `__init__.py` | `component_language()` for `.hwd`, `device_language()` for `.dev` |
| Path constants | `definitions.py` | `BOARD_MODEL_REPO_PATH`, `PERIPHERAL_MODEL_REPO_PATH` etc. — env-overridable |
| Grammar syntax | `grammar/*.tx` | `device.tx` (main), `component.tx`, `communication.tx`, `common.tx` |
| CLI commands | `cli/cli.py` | Click: `validate`, `generate` (rpi/riot/svg/docs/infrastructure) |

## CODE MAP

| Symbol | Location | Role |
|--------|----------|------|
| `component_language` | `__init__.py:9` | `@language('demol-component', '*.hwd')` |
| `device_language` | `__init__.py:14` | `@language('demol-device', '*.dev')` |
| `BOARD_MODEL_REPO_PATH` | `definitions.py:25` | Env-overridable board model directory |
| `PERIPHERAL_MODEL_REPO_PATH` | `definitions.py:30` | Env-overridable peripheral model directory |

## CONVENTIONS

- Grammar files use textX syntax (`=`, `*=`, `?=`, `+=` assignments)
- `common.tx` is imported by all other grammar files
- Template naming: `<peripheral>.<target_ext>.j2` (e.g., `bme680.py.j2`, `sensor_bme680.c.j2`)
- Templates organized by platform: `templates/rpi/`, `templates/riot/`, `templates/docs/`, `templates/smauto/`
- `definitions.py` paths are absolute, computed from `__file__`

## ANTI-PATTERNS

- Do NOT hardcode model repository paths — use `definitions.py` constants
- Do NOT import from `demol.api` (internal) — top-level `api/` is the REST service
- Grammar changes require updating both device.tx and corresponding validators
