# demol/lang/ — Language Engine

## OVERVIEW

Metamodel construction, model parsing, semantic validation, and validation reporting for `.dev` and `.hwd` files.

## STRUCTURE

```
lang/
├── __init__.py      # Public API: get_device_mm(), get_component_mm()
├── device.py        # Device metamodel: model_proc(), enrich_model(), validation orchestration
├── component.py     # Component metamodel for .hwd files (boards, sensors, actuators)
├── validation.py    # ValidationReporter + ValidationResult — rich console output
├── semantics.py     # LEGACY monolith (1776 lines) — DO NOT EXTEND
└── semantics/       # NEW modular validator framework (migration in progress)
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Build device metamodel | `__init__.py` | `get_device_mm()` — registers grammar, validators, scope providers |
| Model post-processing | `device.py` | `model_proc()` — enrichment + validation pipeline |
| Add validation rule | `semantics/validators/` | Inherit `BaseValidator` — see `semantics/README.md` |
| Validation output | `validation.py` | `ValidationReporter` for rich error/warning display |

## CODE MAP

| Symbol | Location | Role |
|--------|----------|------|
| `get_device_mm()` | `__init__.py` | Builds textX metamodel for `.dev` files |
| `get_component_mm()` | `__init__.py` | Builds textX metamodel for `.hwd` files |
| `model_proc(model)` | `device.py` | Post-parse: enrich model → run all validators |
| `enrich_model(model)` | `device.py` | Resolves component references, computes derived properties |
| `ValidationReporter` | `validation.py` | Rich-formatted validation output (errors, warnings, passed rules) |
| `ValidationResult` | `validation.py` | Dataclass: status, errors, warnings, passed_rules |

## ANTI-PATTERNS

- **NEVER add validators to `semantics.py`** — it's a 1776-line legacy monolith being migrated
- New validators go in `semantics/validators/` following `BaseValidator` pattern
- `semantics.py` and `semantics/` directory coexist — both are imported; the monolith provides backward-compatible function exports
- Do NOT call `raise TextXSemanticError` directly — use `raise_validation_error()` from `semantics/core.py` to collect errors

## CONVENTIONS

- Validation errors are **collected** (not raised immediately) via `raise_validation_error()`
- Warnings use `raise_validation_warning()` — for non-critical issues
- `check_validation_errors()` raises after all validators run
- Rule names follow pattern: `[Category-Rule]` (e.g., `[Conn-Power]`, `[Safety-Pin-Conflicts]`, `[WF-All-Peripherals-Connected]`)
