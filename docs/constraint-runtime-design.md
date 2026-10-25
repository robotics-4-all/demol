# CONSTRAINT Runtime Design

**Revision 1.0 | 2026-06-25**

This document describes how user-defined CONSTRAINT expressions (introduced in
the DSL grammar at `demol/grammar/device.tx:141-213`) are evaluated at runtime
on the three hardware backends: Raspberry Pi (raspbian), RIOT OS (riotos), and
Zephyr RTOS (zephyr).

---

## Table of Contents

1. [Scope and Terminology](#1-scope-and-terminology)
2. [RPi Backend (raspbian)](#2-rpi-backend-raspbian)
3. [RIOT Backend (riotos)](#3-riot-backend-riotos)
4. [Zephyr Backend (zephyr)](#4-zephyr-backend-zephyr)
5. [Grammar Recap](#5-grammar-recap)
6. [Built-In Functions Reference](#6-built-in-functions-reference)
7. [Future Work](#7-future-work)

---

## 1. Scope and Terminology

### 1.1 What This Document Covers

Each backends section specifies three runtime concerns:

- **Data sources** -- The runtime variables or data structures that back the
  built-in functions `count()`, `sum_power()`, `avg_power()`, and `max_power()`.
- **Trigger schedule** -- When the constraint check fires (default intervals,
  configurable rates).
- **Failure action** -- What happens when a constraint evaluates to false.
- **Minimal implementation** -- Template files, helper functions, and codegen
  changes needed to produce the runtime.

### 1.2 Validation vs. Runtime

Constraint expressions are currently evaluated at **validation time** by
`UserConstraintValidator` in `demol/lang/semantics/validators/user_constraints.py`
(422 lines). That pass reads the static model only -- it counts peripherals from
the parsed AST, sums declared `POWER.max` values, and checks arithmetic. The
design below extends this to **runtime**: the same expressions are compiled into
backend-specific checks that run on the live device.

### 1.3 Expression Grammar (Recap)

From `demol/grammar/device.tx`:

```
CONSTRAINT <name>: <expr> [MESSAGE "<string>"];

<expr> ::= <comparison>
<comparison> ::= <additive> <op> <additive>
<additive> ::= <multiplicative> (('+'|'-') <multiplicative>)*
<multiplicative> ::= <atom> (('*'|'/') <atom>)*
<atom> ::= <func_call> | <property_access> | <number> | <string> | <bool>
<func_call> ::= count(SENSOR|ACTUATOR|PERIPHERAL|CONNECTION)
             | sum_power(SENSOR|ACTUATOR|PERIPHERAL)
             | avg_power(SENSOR|ACTUATOR|PERIPHERAL)
             | max_power(SENSOR|ACTUATOR|PERIPHERAL)
<property_access> ::= <ID> ('.' <ID>)+
```

---

## 2. RPi Backend (raspbian)

### 2.1 Data Sources

The RPi runtime is Python-based (commlib-py). Each generated peripheral class
resides in its own module (`<peripheral>_<instance>.py`). Constraint checks read
from a shared global registry:

```python
# Generated in constraints.py
import threading

_registry = {}
_registry_lock = threading.Lock()

def register_peripheral(name: str, kind: str, power_mw: float):
    with _registry_lock:
        _registry[name] = {
            "kind": kind,        # "Sensor", "Actuator", "Peripheral"
            "power_mw": power_mw,
            "connected": True,
        }
```

| Built-in | Runtime Data Source |
|----------|-------------------|
| `count(SENSOR)` | `sum(1 for v in _registry.values() if v["kind"] == "Sensor")` |
| `count(ACTUATOR)` | Same, filtered by `"Actuator"` |
| `count(PERIPHERAL)` | `len(_registry)` |
| `count(CONNECTION)` | `sum(1 for v in _registry.values() if v["connected"])` |
| `sum_power(PERIPHERAL)` | `sum(v["power_mw"] for v in _registry.values() if v["power_mw"] is not None)` |
| `avg_power(PERIPHERAL)` | `sum_power(...) / count(PERIPHERAL)` |
| `max_power(PERIPHERAL)` | `max(v["power_mw"] for v in _registry.values() if v["power_mw"] is not None)` |
| `PeripheralName.attribute` | Looked up via `_registry["PeripheralName"].get("attribute")` |

Each peripheral's `__init__` calls `register_peripheral()` so the registry is
populated at startup. The `check_constraints()` function (see 2.4) snapshots
the registry under the lock to avoid data races in threaded contexts.

### 2.2 Trigger Schedule

Default: **every 60 seconds**, driven by a background `threading.Timer` loop.

```python
def _constraint_loop():
    while True:
        check_constraints()
        time.sleep(60.0)
```

The default interval is conservative because (a) power readings change slowly on
RPi peripherals, and (b) the overhead of Python dict iteration is negligible at
60 s granularity.

**Configurable rate.** The plan (T11) adds a `WITH rate = N hz` clause to
`CONSTRAINT` blocks. When present, the generated code uses the override:

```python
_CONSTRAINT_RATE = 10.0  # seconds from 1/rate_hz
```

A rate of `10 hz` means `sleep(0.1)`. The minimum practical rate is `1 hz` on
RPi (100 ms resolution); below that, timer jitter dominates.

### 2.3 Failure Action

Default action:

1. **Log** -- `logging.warning("[Constraint-Violated] %s: %s", name, message)`.
2. **Increment counter** -- A `constraint_failures` counter in the `constraints`
   module is incremented. A counter of zero means all constraints passed.
3. **Callback** -- If an `on_constraint_violated` hook is registered (future
   ALERT integration), it fires here.

```python
# Generated in check_constraints()
constraint_failures = 0

def check_constraints():
    global constraint_failures
    for name, predicate, message in _CONSTRAINTS:
        if not predicate():
            constraint_failures += 1
            logger.warning(
                "[Constraint-Violated] %s: %s (failures=%d)",
                name, message or "expression is false", constraint_failures,
            )
```

The global counter is exposed as `constraints.constraint_failures` so that
ALERT triggers (future work) can react to sustained violations.

### 2.4 Minimal Implementation

**New template file:** `demol/templates/rpi/constraints.py.j2`

The template receives the model's `constraints` list (each with `name`, `expr`,
`message`) and emits:

- `_registry`: dict-based global store keyed by peripheral instance name.
- `register_peripheral()`: called from each peripheral's `__init__`.
- `_CONSTRAINTS`: list of `(name, callable_predicate, message)` tuples built
  at module load.
- `check_constraints()`: evaluates every predicate, logs violations, increments
  counter.

**New helper in `RPiCodeGenerator`:**
- `_generate_constraints()`: renders `constraints.py.j2` and writes it to the
  output directory. Called from `RPiCodeGenerator.generate()`.

**Modification to every peripheral `.py.j2` template:** append a call to
`register_peripheral(instance_name, kind, power_mw)` at the end of `__init__`.

**Codegen guard:** emit nothing when `model.constraints` is empty.

---

## 3. RIOT Backend (riotos)

### 3.1 Data Sources

The RIOT runtime is a single C firmware image. Constraint data lives in global
or file-scope variables declared in a generated `constraint.c`:

```c
/* Generated — constraint.c */
#include <stdint.h>

#define MAX_PERIPHERALS 16

typedef struct {
    const char *name;
    uint8_t kind;        /* 0=Sensor, 1=Actuator, 2=Peripheral */
    int32_t power_mW;    /* -1 if unknown */
    uint8_t connected;
} peripheral_entry_t;

static peripheral_entry_t _peripherals[MAX_PERIPHERALS];
static uint8_t _peripheral_count = 0;
```

| Built-in | Runtime Data Source (C expression) |
|----------|-----------------------------------|
| `count(SENSOR)` | `_count_kind(0)` -- iterates `_peripherals`, counts `kind == 0` |
| `count(ACTUATOR)` | `_count_kind(1)` |
| `count(PERIPHERAL)` | `_peripheral_count` |
| `count(CONNECTION)` | `_count_connected()` -- counts `connected == 1` |
| `sum_power(PERIPHERAL)` | `_sum_power_mW()` -- sums `power_mW` where `>= 0` |
| `avg_power(PERIPHERAL)` | `sum_power() / count(PERIPHERAL)` (integer division, rounding down) |
| `max_power(PERIPHERAL)` | `_max_power_mW()` -- max of `power_mW` |
| `PeripheralName.attribute` | Not directly supported in initial version (planned for follow-up) |

Each peripheral driver's `init()` function calls `_register_peripheral(name, kind, power_mW)` to populate the table at boot.

### 3.2 Trigger Schedule

Default: **every 30 seconds**, driven by a periodic timer in the RIOT event
loop.

```c
/* In main.c */
static xtimer_t _constraint_timer;

static void _constraint_cb(void *arg) {
    (void)arg;
    check_constraints();
    xtimer_set(&_constraint_timer, 30 * US_PER_SEC);
}

void constraint_init(void) {
    xtimer_set(&_constraint_timer, 30 * US_PER_SEC);
}
```

30 seconds is a middle ground: RIOT firmware runs on battery-backed ESP32
devices where power is a first-class concern, but checking every 10 s would
add measurable CPU wake cycles.

**Configurable rate.** When `CONSTRAINT ... WITH rate = 10 hz` is specified,
the generated code uses a compile-time macro:

```c
#define CONSTRAINT_CHECK_INTERVAL_US  (1000000ULL / 10)   /* 100 ms */
#define CONSTRAINT_CHECK_INTERVAL_US  (1000000ULL / CONSTRAINT_RATE_HZ)
```

### 3.3 Failure Action

Default action:

1. **Log via `LOG_WARNING`** -- RIOT's logging system: `LOG_WARNING("[Constraint-Violated] %s: %s\n", name, msg)`.
2. **Increment counter** -- A `static uint32_t constraint_failures` counter in
   `constraint.c`.
3. **Publish** (optional, future) -- If MQTT is enabled, the failure can be
   published as a JSON message.

```c
static uint32_t constraint_failures = 0;

void check_constraints(void) {
    for (uint8_t i = 0; i < _constraint_count; i++) {
        int result = _eval_predicate(i);
        if (!result) {
            constraint_failures++;
            LOG_WARNING("[Constraint-Violated] %s: %s (failures=%"PRIu32")\n",
                        _constraints[i].name,
                        _constraints[i].message,
                        constraint_failures);
        }
    }
}
```

### 3.4 Minimal Implementation

**New template files:**
- `demol/templates/riot/constraint.c.j2` -- C source with the peripheral table,
  helper functions (`_count_kind`, `_sum_power_mW`, `_max_power_mW`),
  `_eval_predicate(i)`, and `check_constraints()`.
- `demol/templates/riot/constraint.h.j2` -- Public header declaring
  `register_peripheral()`, `constraint_init()`, and `check_constraints()`.

**Modifications to existing templates:**
- `demol/templates/riot/main.c.j2` -- add `#include "constraint.h"` and call
  `constraint_init()` before entering the main loop.
- `demol/templates/riot/Makefile.j2` -- add `constraint.c` to the source list.

**Modification to every RIOT peripheral driver `.c.j2`:** call
`register_peripheral(name, kind, power_mW)` in the init function.

**Codegen guard:** emit nothing when `model.constraints` is empty.

---

## 4. Zephyr Backend (zephyr)

### 4.1 Data Sources

Zephyr uses a devicetree-driven build model. The generated `main.c` declares a
global `device_state` struct that tracks peripheral runtime data:

```c
/* Generated — constraint.c for Zephyr */
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
LOG_MODULE_REGISTER(constraint, LOG_LEVEL_WRN);

#define MAX_PERIPHERALS 16

struct periph_state {
    const char *name;
    uint8_t kind;         /* 0=Sensor, 1=Actuator, 2=Peripheral */
    int32_t power_mW;     /* -1 if unknown / not measured */
    bool connected;
};

static struct periph_state _devices[MAX_PERIPHERALS];
static uint8_t _device_count = 0;
static struct k_mutex _state_mutex;
```

| Built-in | Runtime Data Source (C expression) |
|----------|-----------------------------------|
| `count(SENSOR)` | `_count_kind(0)` -- walks `_devices[]`, counts `kind == 0` |
| `count(ACTUATOR)` | `_count_kind(1)` |
| `count(PERIPHERAL)` | `_device_count` |
| `count(CONNECTION)` | `_count_connected()` |
| `sum_power(PERIPHERAL)` | `_sum_power_mW()` -- sums `power_mW` fields |
| `avg_power(PERIPHERAL)` | `sum_power() / count(PERIPHERAL)` (integer, rounded) |
| `max_power(PERIPHERAL)` | `_max_power_mW()` -- walks array for maximum |

Zephyr drivers register themselves via a `register_peripheral()` call placed
in each generated driver's init function. The `k_mutex` protects against
concurrent access from multiple Zephyr threads.

### 4.2 Trigger Schedule

Default: **every 10 seconds**, driven by a Zephyr delayed workqueue item:

```c
/* In constraint.c */
static struct k_work_delayable _constraint_work;

static void _constraint_work_handler(struct k_work *work) {
    ARG_UNUSED(work);
    check_constraints();
    k_work_schedule(&_constraint_work, K_SECONDS(10));
}

void constraint_init(void) {
    k_mutex_init(&_state_mutex);
    k_work_schedule(&_constraint_work, K_SECONDS(10));
}
```

10 seconds is the most aggressive default of the three backends. Zephyr targets
(ESP32, native_sim) have more CPU headroom than RIOT, and the Zephyr workqueue
infrastructure makes lightweight periodic checks cheap.

**Configurable rate.** With `WITH rate = 20 hz`, the generated code uses:

```c
#define CONSTRAINT_CHECK_INTERVAL_MS  (1000U / 20)  /* 50 ms */
k_work_schedule(&_constraint_work, K_MSEC(CONSTRAINT_CHECK_INTERVAL_MS));
```

### 4.3 Failure Action

Default action:

1. **Log via `LOG_WRN`** -- Zephyr's logging subsystem:
   `LOG_WRN("[Constraint-Violated] %s: %s", name, message)`.
2. **Atomic counter** -- A `static atomic_t constraint_failures` counter,
   incremented with `atomic_inc()`.
3. **Future alert callback** -- The counter is readable by the ALERT subsystem
   (task T15) via `get_constraint_failure_count()`.

```c
static atomic_t constraint_failures;

void check_constraints(void) {
    for (uint8_t i = 0; i < _constraint_count; i++) {
        if (!_eval_predicate(i)) {
            atomic_inc(&constraint_failures);
            LOG_WRN("[Constraint-Violated] %s: %s",
                    _constraints[i].name,
                    _constraints[i].message ? _constraints[i].message : "expression is false");
        }
    }
}
```

### 4.4 Minimal Implementation

**New template files:**
- `demol/templates/zephyr/constraint.c.j2` -- C source with `struct periph_state`,
  `register_peripheral()`, `count`/`sum`/`avg`/`max` helpers, `check_constraints()`,
  and the `k_work_delayable` loop.
- `demol/templates/zephyr/constraint.h.j2` -- Header declaring the public API.

**Modifications to existing templates:**
- `demol/templates/zephyr/main.c.j2` -- add `#include "constraint.h"` and call
  `constraint_init()` at the start of `main()`.
- `demol/templates/zephyr/CMakeLists.txt.j2` -- add `constraint.c` to the
  `target_sources()` list.

**Modification to each Zephyr peripheral driver `.c.j2`:** insert a call to
`register_peripheral()` at the end of the peripheral's init path.

**Codegen guard:** emit nothing when `model.constraints` is empty.

---

## 5. Grammar Recap

The relevant grammar rules from `demol/grammar/device.tx:141-213`:

```
UserConstraint:
    'CONSTRAINT' name=ID ':' expr=ConstraintExpr
    ('MESSAGE' message=STRING)?
    ';'
;

ConstraintExpr -> ComparisonExpr;

ComparisonExpr:
    left=AdditiveExpr op=ComparisonOp right=AdditiveExpr
;

ComparisonOp: '<=' | '>=' | '!=' | '==' | '<' | '>';

AdditiveExpr:
    operands=UnaryExpr (operators=AdditiveOp operands=UnaryExpr)*
;

MultiplicativeExpr:
    operands=AtomExpr (operators=MultiplicativeOp operands=AtomExpr)*
;

AtomExpr:
    FunctionCallExpr | PropertyAccessExpr | NumberLiteral
    | StringLiteral | BoolLiteral
;

FunctionCallExpr:
    func=BuiltinFunc '(' arg=FunctionArg ')'
;

BuiltinFunc: 'count' | 'sum_power' | 'avg_power' | 'max_power';
FunctionArg: 'SENSOR' | 'ACTUATOR' | 'PERIPHERAL' | 'CONNECTION';
```

At runtime, the codegen compiles each `ConstraintExpr` AST into a backend-specific
predicate function. For example, `sum_power(PERIPHERAL) < 500 mW` becomes:

| Backend | Generated Predicate |
|---------|-------------------|
| RPi | `(lambda: sum(v["power_mw"] for v in _registry.values() if v["power_mw"] is not None) < 500.0)` |
| RIOT | `(_sum_power_mW() < 500)` |
| Zephyr | `(_sum_power_mW() < 500)` |

---

## 6. Built-In Functions Reference

This section documents the four built-in functions as they appear in the
validation-time evaluator (`user_constraints.py:138-174`), quoted for reference,
and describes their runtime semantics.

### 6.1 `count(kind)`

**Validation signature** (from `user_constraints.py:147-150`):

```python
if func_name == "count":
    if arg == "CONNECTION":
        return float(len(getattr(model, "connections", [])))
    return float(len(_get_peripherals_by_kind(model, arg)))
```

**Runtime semantics:**

| Backend | Implementation |
|---------|---------------|
| RPi | `sum(1 for v in _registry.values() if v["kind"] matches)` |
| RIOT | `_count_kind(kind_code)` -- walks `_peripherals[]` array |
| Zephyr | `_count_kind(kind_code)` -- walks `_devices[]` array |

### 6.2 `sum_power(kind)`

**Validation signature** (from `user_constraints.py:152-173`):

```python
if func_name in ("sum_power", "avg_power", "max_power"):
    peripherals = _get_peripherals_by_kind(model, arg)
    power_values = []
    for p in peripherals:
        ref = p.ref if hasattr(p, "ref") else p
        op = getattr(ref, "operational", None)
        if op is None:
            continue
        p_max = _parse_power_mw(getattr(op, "max", None))
        if p_max is not None:
            power_values.append(p_max)
    ...
    if func_name == "sum_power":
        return sum(power_values)
```

**Runtime semantics:**

Each peripheral's power value comes from its `.hwd` `operational.max` at
codegen time. The runtime simply aggregates the declared values. Future
iterations may replace declared values with measured consumption.

### 6.3 `avg_power(kind)`

Returns `sum_power(kind) / count(kind)`. If `count(kind)` is zero, returns 0.0.

### 6.4 `max_power(kind)`

Returns the maximum `operational.max` value across all peripherals of the
given kind. Falls back to 0.0 if no peripherals exist.

### 6.5 Property Access (`PeripheralName.attribute`)

Property access is evaluated at runtime by looking up the peripheral instance
in the registry and reading the named attribute. Attribute sources are:

| Source | Priority | Example |
|--------|----------|---------|
| User-defined attribute (WITH clause) | Highest | `ZoneSensor1.my_flag` |
| Operational attribute (`.hwd` max/min/avg) | Medium | `ZoneSensor1.power_max` |
| Peripheral type attribute (`.hwd` defaults) | Lowest | `BME680.vcc` |

The same priority order is used by the validation-time evaluator
(`user_constraints.py:229-254`).

---

## 7. Future Work

### 7.1 Per-Constraint Rate Override

The grammar currently has no `WITH rate = N hz` clause on `CONSTRAINT` blocks.
A future grammar change would add:

```
UserConstraint:
    'CONSTRAINT' name=ID ':' expr=ConstraintExpr
    ('MESSAGE' message=STRING)?
    ('WITH' 'rate' '=' rate=NUMBER rate_unit=FrequencyUnit)?
    ';'
;
```

When present, the generated code uses the per-constraint rate instead of the
backend default. When multiple constraints have different rates, the check
loop runs at the LCM (least common multiple) of all rates, or more practically,
at the fastest rate.

### 7.2 ALERT Integration

Constraint violations are a natural trigger for the ALERT subsystem. A future
extension could add a `CONSTRAINT_VIOLATED` event source to the ALERT condition
grammar:

```
ALERT power_warning ON CONSTRAINT sensor_redundancy
    WHEN constraint_failures > 3
    THEN PUBLISH "alerts/power" VIA Cloud COOLDOWN 60 sec;
```

This requires:
- Exposing `constraint_failures` as a readable value in the ALERT runtime.
- Adding `ON CONSTRAINT <name>` as a valid ALERT source (currently only
  `ON <sensor>` is supported).

### 7.3 Broker-Based Reporting

Constraint violations could be published to the MQTT broker directly without
requiring an ALERT block. A future `ON VIOLATION PUBLISH` clause:

```
CONSTRAINT power_ok: sum_power(PERIPHERAL) < 500 mW
    MESSAGE "over budget"
    ON VIOLATION PUBLISH "constraints/power" VIA Cloud;
```

This would generate a `mqtt_publish()` call inside the violation handler
instead of just logging.

### 7.4 Measured Power Tracking

The current runtime uses declared `operational.max` values from `.hwd` files.
A future iteration could replace these with real measurements from current
sensors or fuel-gauge ICs, updating the registry at each SAMPLING tick.

### 7.5 Cross-Backend Library

The `count`, `sum_power`, `avg_power`, and `max_power` helpers share the same
logic across all three C backends. Consider extracting a shared C header
(`demol/templates/include/constraint_helpers.h.j2`) that can be `#include`d by
both RIOT and Zephyr templates, reducing duplication in T12 and T13.
