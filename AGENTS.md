# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-22
**Commit:** 4a28eca
**Branch:** devel

## OVERVIEW

DeMoL (Device Modeling Language) — a textX-based Python DSL for hardware-aware IoT device modeling with automated code generation (Raspberry Pi Python, RiotOS C), semantic validation (electrical safety, pin conflicts, protocol constraints), power budget analysis, SmartConnect auto-wiring, SAMPLING blocks, CONSTRAINT expressions, ALERT triggers, and a React visual designer with LSP for IDE integration.

## STRUCTURE

```
demol/                  # Core DSL package (grammar, semantics, codegen)
├── grammar/            # 4 textX grammar files (.tx)
├── lang/               # Language engine: parsing, validation, semantics
│   ├── semantics.py    # LEGACY validator monolith (1727 lines) — DO NOT EXTEND
│   ├── semantics/      # NEW modular validator framework (14 validator classes)
│   └── smart_connection.py  # SMARTCONNECT auto-wiring resolution (703 lines)
├── transformations/    # M2T/M2M generators (rpi, riot, svg, docs, pinmap, smauto, json)
├── builtin_models/     # Hardware library: boards (.hwd), peripherals (.hwd), power
├── templates/          # Jinja2 templates per platform (rpi/, riot/, docs/, smauto/)
├── cli/                # Click CLI: validate, generate, analyze, fix, diff, lsp
├── lsp/                # Language Server Protocol server
└── api/                # Internal API module (not the top-level api/)
app/                    # React + Vite + React Flow visual designer (TypeScript)
api/                    # FastAPI REST backend (validation + generation endpoints)
tests/                  # pytest suite: 33 test files + models/valid/ + models/invalid/
examples/               # Device models: rpi/ (22), esp/ (3), smauto/ (5)
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
| SmartConnect logic | `demol/lang/smart_connection.py` | Auto pin assignment resolution (703 lines) |
| Auto-fix engine | `demol/cli/autofix.py` | Detects and corrects common validation errors |
| Model diff engine | `demol/cli/modeldiff.py` | Semantic comparison of two `.dev` models |
| LSP server | `demol/lsp/server.py` | textX LSP: diagnostics, completion, hover, go-to-def |

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
| `validate_power_connection` | function | `demol/lang/semantics.py` | Power validation (voltage compat, GND rules) — legacy |
| `ValidationReporter` | class | `demol/lang/validation.py` | Rich console validation output |
| `ValidationResult` | class | `demol/lang/validation.py` | Dataclass: status, errors, warnings, passed_rules |
| `enrich_model` | function | `demol/lang/device.py` | Resolves refs, SmartConnect, VIA routing, auto-topics |
| `demol_to_json` / `json_to_demol` | functions | `demol/transformations/json_demol.py` | Bidirectional DSL ↔ JSON conversion |

## CONVENTIONS

- **Line length**: flake8=120 (setup.cfg + Makefile both use 120), ignores E203/E501
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
- `semantics.py` (1727 lines) is the legacy monolith; new validators go in `semantics/validators/` — do NOT add to the monolith
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
demol lsp                                           # Start LSP server for IDE integration

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
- `setup.cfg` flake8 config (120 chars) matches Makefile lint target (120 chars)
- Frontend (`app/`) proxies API calls to backend on port 8000 via `/api` prefix
- API requires `X-API-Key` header for authentication
- `demol/definitions.py` paths use `os.getenv()` for overridable model repos (BOARD_MODEL_REPO_PATH, etc.)
- 33 test files covering 315+ test cases; CI runs across Python 3.9–3.13 matrix
- `demol/lang/smart_connection.py` (703 lines) handles SMARTCONNECT auto-wiring resolution
