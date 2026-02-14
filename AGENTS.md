# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-14
**Commit:** b6d3665
**Branch:** devel

## OVERVIEW

DeMoL (Device Modeling Language) — a textX-based Python DSL for hardware-aware IoT device modeling with automated code generation (Raspberry Pi Python, RiotOS C), semantic validation (electrical safety, pin conflicts, protocol constraints), and a React visual designer.

## STRUCTURE

```
demol/                  # Core DSL package (grammar, semantics, codegen)
├── grammar/            # 4 textX grammar files (.tx)
├── lang/               # Language engine: parsing, validation, semantics
│   └── semantics/      # Modular validator framework (migrating from monolith)
├── transformations/    # M2T/M2M generators (rpi, riot, svg, docs, smauto, json)
├── builtin_models/     # Hardware library: boards (.hwd), peripherals (.hwd), power
├── templates/          # Jinja2 templates per platform (rpi/, riot/, docs/, smauto/)
├── cli/                # Click CLI entry point
└── api/                # Internal API module (not the top-level api/)
app/                    # React + Vite + React Flow visual designer (TypeScript)
api/                    # FastAPI REST backend (validation + generation endpoints)
tests/                  # pytest suite: 19 test files + models/valid/ + models/invalid/
examples/               # Device models: rpi/ (12), esp/ (3), smauto/ (5)
scripts/                # Automation: validation, generation, evaluation
docker/                 # Dockerfiles (api, app, tests) + docker-compose.yml
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
| Add REST endpoint | `api/main.py` | FastAPI, secured with X-API-Key header |
| Add CLI command | `demol/cli/cli.py` | Click framework |
| Add frontend component | `app/src/components/` | React + TypeScript, nodes in `components/nodes/` |
| Write tests | `tests/` | pytest; use `device_mm`/`component_mm` fixtures from `conftest.py` |
| Add example model | `examples/rpi/` or `examples/esp/` | `.dev` files |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `component_language` | function | `demol/__init__.py` | textX registration for `.hwd` files |
| `device_language` | function | `demol/__init__.py` | textX registration for `.dev` files |
| `get_device_mm` | function | `demol/lang/__init__.py` | Builds device metamodel with validators |
| `get_component_mm` | function | `demol/lang/__init__.py` | Builds component metamodel |
| `model_proc` | function | `demol/lang/device.py` | Model post-processing: enrichment + validation |
| `BaseCodeGenerator` | class | `demol/transformations/base_generator.py` | Abstract code generator with model querying |
| `RPiCodeGenerator` | class | `demol/transformations/m2t_rpi.py` | Raspberry Pi Python generator |
| `RiotCodeGenerator` | class | `demol/transformations/m2t_riot.py` | RiotOS C generator |
| `validate_power_connection` | function | `demol/lang/semantics.py` | Power validation (voltage compat, GND rules) |
| `ValidationReporter` | class | `demol/lang/validation.py` | Rich console validation output |
| `demol_to_json` / `json_to_demol` | functions | `demol/transformations/json_demol.py` | Bidirectional DSL ↔ JSON conversion |

## CONVENTIONS

- **Line length**: flake8=80 (setup.cfg), black=120 (Makefile) — Makefile targets override setup.cfg
- **Grammar files**: `.tx` extension, textX syntax. 4 modular files imported via `common.tx`
- **Model files**: `.dev` (device definitions), `.hwd` (hardware components)
- **Templates**: `.j2` Jinja2, named `<component>.<ext>.j2` (e.g., `bme680.py.j2`)
- **Tests**: `test_<domain>_<aspect>.py`, inline DSL strings, session-scoped fixtures
- **Validators**: Class-based (`BaseValidator` subclass), organized by category in `validators/`
- **Semantic errors**: `raise_validation_error(node, message, rule_name)` — collected, not raised immediately
- **Semantic warnings**: `raise_validation_warning(node, message, rule_name)` — for non-critical issues (IO voltage mismatch, missing GND)

## ANTI-PATTERNS (THIS PROJECT)

- **NEVER** suppress semantic validation errors without `--skip-semantics` flag
- **NEVER** reuse board pins across connections (except I2C SDA/SCL and power pins which are shareable)
- **NEVER** connect GND to VCC or vice versa (PC-NO-MIX rule)
- **NEVER** use I2C addresses outside 0x00-0x7F range
- Voltage tolerance is 0.5V — connections exceeding this are errors, not warnings
- `semantics.py` (1776 lines) is the legacy monolith; new validators go in `semantics/validators/` — do NOT add to the monolith

## UNIQUE STYLES

- DSL uses uppercase keywords: `DEVICE`, `BOARD`, `SENSOR`, `ACTUATOR`, `CONNECT`, `POWER`, `DATA`, `USE`, `BROKER`, `NETWORK`
- Pin syntax: `name[function] @ number` (e.g., `GPIO4[gpio,adc] @ 7`)
- Connection syntax: `protocol[props] board_pin -- peripheral_pin`
- `@` in CONNECT block specifies message broker topic
- Formal semantics spec in `SEMANTICS.md` (mathematical notation, inference rules)

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
demol generate svg examples/rpi/multi_periph.dev --output-dir ./diagrams
demol generate docs examples/rpi/multi_periph.dev --output-dir ./docs

# Test
make test                           # pytest tests/
make test-local                     # pytest + validation + transformations
make test-cov                       # with coverage

# Quality
make lint                           # flake8
make format                         # black
make type-check                     # mypy

# Docker
./start.sh                          # Full stack: API (8000) + Frontend (5173)
make docker-test                    # Tests in container
```

## NOTES

- `RIOT/` is a full OS checkout (~40k files) — exclude from searches/analysis
- `build/` contains generated output — do not edit manually
- `venv/` and `.venv/` are virtual environments — exclude from searches
- `demol/lang/semantics.py` and `demol/lang/semantics/` coexist — migration in progress (see `semantics/README.md`)
- `setup.cfg` flake8 config (80 chars) conflicts with Makefile lint target (120 chars) — Makefile wins in practice
- Frontend (`app/`) proxies API calls to backend on port 8000
- API requires `X-API-Key` header for authentication
- `demol/definitions.py` paths use `os.getenv()` for overridable model repos (BOARD_MODEL_REPO_PATH, etc.)
