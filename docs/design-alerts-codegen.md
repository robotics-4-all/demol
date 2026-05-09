# ALERT Codegen — Design Document

**Status:** PROPOSED — awaiting implementation approval
**Author:** Morpheus
**Date:** 2026-05-09
**Scope:** Emit runtime code for `ALERT` blocks parsed by the DeMoL grammar (current behavior: parsed + validated, never emitted).

---

## 1. Problem Statement

ALERT blocks are first-class DSL citizens (grammar `device.tx:215-251`, validator `validators/alert.py`, used by 11 example `.dev` files), but `RPiCodeGenerator` and `RiotCodeGenerator` ignore `model.alerts` entirely. Generated runtimes never check thresholds, never publish alerts, never trigger ACTIVATE actions. **Silent codegen drop.**

A user writing:

```
ALERT fever_alert ON IRThermometer
  WHEN object_temperature > 37.5
  THEN PUBLISH "health/alerts/fever" VIA HealthGateway
       ACTIVATE StatusLed
  COOLDOWN 60 sec;
```

…gets a passing `validate`, but the generated `irthermometer_node.py` contains no alert logic.

---

## 2. AST Shape (what we have to work with)

Confirmed via live `build_model`:

```python
m.alerts: List[AlertTrigger]

AlertTrigger:
  name: str                       # "fever_alert"
  source: ComponentInstance       # resolved cross-ref → .name = "IRThermometer"
  condition: AlertConditionExpr   # tree of AlertComparison nodes joined by &&/||
  actions: List[AlertPublish | AlertActivate]
  cooldown: float | None          # 60
  cooldown_unit: str | None       # "sec" / "hz"  (NB: hz is semantically wrong for cooldown; document)

AlertComparison:
  property: str                   # "object_temperature"
  op: str                         # ">" / "<" / ">=" / "<=" / "==" / "!="
  value: float
  unit: str | None                # "celsius" etc — informational only

AlertPublish:
  topic: str                      # "health/alerts/fever"
  via: str | None                 # broker NAME (not a ref). Resolve via m.brokers.

AlertActivate:
  target: ComponentInstance       # resolved → publishes to target's CONNECT @ topic
```

Every alert is bound to **exactly one source peripheral**. Its property names must match the keys produced by that source's `update_state_data(data)` call (e.g., BME680 → temperature/pressure/humidity/gas_resistance; MAX30102 → heart_rate_bpm/spo2; etc.). **No central registry maps these today** — they're informal contracts inside each `<peripheral>.py.j2`. The validator only checks structural well-formedness, not property name validity.

---

## 3. Design Principles

1. **Co-locate alert logic with the source's runtime** — alerts fire after sampling, where the data is. No separate alert daemon. Lower latency, simpler ownership.
2. **Re-use existing transports** — RPi already has commlib `Node` per peripheral; reuse it for the publish. RIOT already has `mqtt_broker.c` with `publish()`.
3. **Multi-broker awareness** — VIA may name a broker different from the source's data broker. RPi nodes currently know only one broker config; we extend to N.
4. **Cooldown as wall-clock duration** — accept `sec`, `min`, `hr`. Reject `hz` at generation time with a warning (it's nonsensical for cooldown). Default unit if absent: `sec`.
5. **ACTIVATE as a publish to the actuator's subscribe topic** — the target peripheral already subscribes to its `CONNECT @ "topic"`. Publishing the right message there triggers it. No new transport mechanism required.
6. **Fail-closed on property mismatch** — if `condition.property` isn't in the most recent `current_state['data']` dict, log a warning at runtime and skip the check (don't crash). Log once per property to avoid spam.
7. **Idempotent emission** — same model → same generated code. No timestamps in output.

---

## 4. RPi Implementation Sketch

### 4.1 New helper module: `demol/templates/rpi/alerts.py.j2`

A small library that each sensor/actuator node imports. Pure runtime — no Jinja per-alert logic here.

```python
import time
from typing import Any, Callable, Dict, List, Optional


class AlertTrigger:
    """Single alert: condition + actions + cooldown.

    Conditions are pre-compiled into a Python lambda by the generator.
    Cooldown is wall-clock seconds (0 = no cooldown).
    """

    __slots__ = ("name", "_check", "_actions", "_cooldown_sec", "_last_fired", "_property_warned")

    def __init__(
        self,
        name: str,
        check: Callable[[Dict[str, Any]], bool],
        actions: List[Callable[[], None]],
        cooldown_sec: float,
    ):
        self.name = name
        self._check = check
        self._actions = actions
        self._cooldown_sec = cooldown_sec
        self._last_fired = 0.0
        self._property_warned = False

    def evaluate(self, data: Dict[str, Any]) -> None:
        try:
            if not self._check(data):
                return
        except (KeyError, TypeError) as e:
            if not self._property_warned:
                print(f"[alert:{self.name}] skipping: {e}")
                self._property_warned = True
            return
        now = time.monotonic()
        if now - self._last_fired < self._cooldown_sec:
            return
        self._last_fired = now
        for action in self._actions:
            try:
                action()
            except Exception as e:  # noqa: BLE001 — runtime resilience
                print(f"[alert:{self.name}] action failed: {e}")
```

### 4.2 Per-source alert binding (extend `sensor_node.py.j2`)

After the `_send` step, evaluate each alert bound to this source:

```jinja2
{% if source_alerts %}
    # --- Generated alert checks ---
    def _check_alerts(self, data):
        for alert in self._alerts:
            alert.evaluate(data)

{% endif %}
```

…and in `__init__`, build `self._alerts` from a generated table (literal Python — no eval, no exec). Conditions become lambdas:

```python
self._alerts = [
    AlertTrigger(
        name="fever_alert",
        check=lambda d: d["object_temperature"] > 37.5,
        actions=[
            lambda: self._alert_pubs["fever_alert_pub_0"].publish({"alert": "fever_alert", "value": d["object_temperature"], "ts": time.time()}),
            lambda: self._alert_pubs["fever_alert_act_0"].publish({"command": "on"}),
        ],
        cooldown_sec=60.0,
    ),
]
```

(Lambdas with closures over `d` are problematic — generator emits proper named functions instead. Sketch above is shorthand.)

### 4.3 Multi-broker connections in nodes

Today each node holds one `ConnectionParameters`. Extend to a dict keyed by broker name, populated by the generator from `model.brokers`:

```jinja2
self._brokers = {
{% for b in brokers %}
    "{{ b.name }}": ConnectionParameters(host="{{ b.host }}", port={{ b.port }}, ...),
{% endfor %}
}
```

Each alert publisher gets its own commlib `Node` bound to the VIA broker (or the default if VIA absent):

```python
self._alert_nodes = {}
self._alert_pubs = {}
# Generator emits one block per (alert × publish-action):
self._alert_nodes["fever_alert_pub_0"] = Node(
    node_name="alerts.fever_alert.0",
    connection_params=self._brokers["HealthGateway"],
    heartbeats=False,
)
self._alert_pubs["fever_alert_pub_0"] = self._alert_nodes["fever_alert_pub_0"].create_publisher(
    msg_type=dict,  # or a generated AlertMessage
    topic="health/alerts/fever",
)
self._alert_nodes["fever_alert_pub_0"].run()
```

For ACTIVATE, the publisher topic = the activated peripheral's `connect.remote` (looked up at generation time):

```python
self._alert_pubs["fever_alert_act_0"] = self._alert_nodes["fever_alert_act_0"].create_publisher(
    msg_type=dict,
    topic="health/status",  # StatusLed's CONNECT @ topic
)
```

The actuator already subscribes there and calls `actuator.write(msg)` — no actuator-side change needed.

### 4.4 Generator changes (`m2t_rpi.py`)

1. Add `BaseCodeGenerator.get_alerts_for_source(source_name) -> List[AlertTrigger]` (groups model.alerts by source).
2. Add `BaseCodeGenerator.resolve_broker(name) -> dict` (lookup by name in model.brokers).
3. Add `BaseCodeGenerator.resolve_activate_target_topic(target) -> str` (find target's `connection.remote`).
4. Extend `build_template_context` to include `source_alerts`, `brokers`, plus per-action resolved metadata (broker_config, target_topic).
5. Always emit `alerts.py` (small helper) regardless of whether any alerts exist; it's harmless if unused.

### 4.5 Diff sketch (≈ +120 LOC across 3 files)

```
demol/templates/rpi/alerts.py.j2          | +60 (new)
demol/templates/rpi/sensor_node.py.j2     | +35 (alert init + evaluate hook)
demol/templates/rpi/actuator_node.py.j2   | +5  (only if actuator can be source — rare; safe NOP)
demol/transformations/base_generator.py   | +30 (3 helper methods)
demol/transformations/m2t_rpi.py          | +15 (context plumbing + emit alerts.py)
```

---

## 5. RIOT Implementation (Phase 2 — SHIPPED)

RIOT alerts inject inline per-driver C checks (no separate runtime, no broker dispatch table). Each alert becomes a static `last_fire_<name>` cooldown tracker plus an `if (condition_c) { … publish_alert(payload, topic); }` block placed inside the driver's `_thread` function right after data is read and before the JSON publish path.

### 5.1 PROPERTIES grammar extension (`demol/grammar/component.tx`)

Both `Sensor` and `Actuator` rules accept an optional `PROPERTIES` section that maps DSL property names to driver-local C expressions:

```
SENSOR[Env] BME680
    PINS sda[i2c]@1, scl[i2c]@2, vcc[VCC]@3, gnd[GND]@4
    PROPERTIES
        temperature -> "data.temperature" : int32 SCALE 100 FOR riotos,
        pressure    -> "data.pressure"    : uint32          FOR riotos,
        humidity    -> "data.humidity"    : int32 SCALE 1000 FOR riotos
    TEMPLATES raspbian="bme680.py.j2", riotos="bme680.c.j2"
```

Each `PeripheralProperty`:

- `name` — DSL property identifier referenced from `WHEN <name> <op> <value>`.
- `expr` — verbatim C expression in scope at the alert injection point (e.g. `data.temperature`, `(state == 0 ? 1 : 0)`).
- `ptype` — one of `int8|uint8|…|int64|uint64|float|double|bool|string`. Integer types trigger an `(int64_t)` cast on the comparison RHS.
- `scale` — optional integer multiplier. The DSL literal is multiplied by SCALE before emission so DSL units (e.g. `38.5 celsius`) translate to the driver's native units (e.g. BME680 stores temperature as int32 in 0.01 °C → SCALE 100 emits `> (int64_t)(3850)`).
- `target` — optional `FOR <os>` tag scoping the property to a single backend (e.g. `riotos`). Untagged properties act as defaults.

Today only `riotos`-tagged properties are consumed; the same mechanism is reusable for future backends.

### 5.2 PROPERTIES validator (`demol/lang/semantics/validators/peripheral_properties.py`)

`PeripheralPropertyValidator` walks `model.connections`, dedups peripheral refs by `id()`, and emits four rules:

| Rule | Severity |
| --- | --- |
| `[Properties-Empty-Expr]` — `expr` must be a non-empty string | error |
| `[Properties-Scale-Positive]` — `SCALE` must be `>= 0` | error |
| `[Properties-Duplicate-Per-Target]` — same `(name, target)` cannot repeat in one peripheral | error |
| `[Properties-Conflicting-Default]` — both untagged and tagged entries for the same name | warning |

Registered in `demol/lang/device.py` immediately before the existing `Alert Triggers` rule so resolver lookups see validated data.

### 5.3 Codegen helpers (`demol/transformations/base_generator.py`)

Three platform-agnostic helpers expose the resolver to all backends:

- `get_alert_property_resolver(peripheral_ref, target='riotos')` — two-pass merge (tagged FOR-target wins over untagged default), returns `{name: {expr, scale, ptype}}`.
- `render_riot_comparison(comparison, resolver)` — emits `({expr}) {op} (int64_t)({int(value*scale)})` for integer types, `({expr}) {op} {float}` for float types, returns `None` if the property is unknown.
- `render_riot_condition(expr, resolver)` — recursive AST walker; leaf = comparison, node = `({left}) && ({right})` or `||`. Returns `None` atomically if any leaf is unrenderable so the caller can drop the whole alert.

Class constants `_RIOT_INT_TYPES` and `_RIOT_COMP_OPS` keep the type/operator mappings co-located.

### 5.4 RIOT alert context (`demol/transformations/m2t_riot.py`)

`RiotCodeGenerator._build_riot_alert_context(instance, pref)` is invoked per driver instance and produces the `source_alerts` list injected into each driver template's context:

```python
{
    "name": "fever_alert",
    "c_safe_name": "fever_alert",          # '-' → '_' for C identifier safety
    "condition_c": "(data.temperature) > (int64_t)(3850)",
    "cooldown_sec": 60,                    # uint64_t literal seconds
    "actions": [
        {
            "kind": "publish",
            "topic": "health/alerts/fever",
            "payload_c": "{\"alert\":\"fever_alert\",\"source\":\"BME\"}",
        },
    ],
}
```

Error handling is fail-soft per alert:

- No PROPERTIES on the peripheral → drop **all** alerts for that source with a logger warning.
- Unrenderable condition (unknown property / unsupported op) → drop **that** alert only.
- `ACTIVATE` with a target that has no `CONNECT @ "topic"` → drop the action with a logger warning.
- `PUBLISH … VIA <non-default-broker>` → log a warning and downgrade to the default broker (RIOT runs a single global `MQTTClient`).

### 5.5 Single-broker constraint (`mqtt_broker.h.j2` + `main.c.j2`)

RIOT's runtime ships one `static MQTTClient client;` and one `static Network network;` in `main.c`. Multi-broker dispatch would require a major refactor of every driver, so Phase 2 keeps the single-client model and surfaces the constraint to the user instead:

```c
/* in mqtt_broker.h.j2 */
void publish_alert(char *payload, char *topic);

/* in main.c.j2 */
void publish_alert(char *payload, char *topic)
{
    mqtt_publish(&client, &network, payload, topic);
}
```

`AlertValidator` mirrors the codegen-time downgrade with rule `[Safety-Alert-RiotMultiBroker]` — when `metadata.os == "riotos"` and an `AlertPublish` references a non-default `VIA`, the validator emits a warning naming the default broker that will actually be used. This makes the contract visible at validate-time, not just at runtime.

### 5.6 Driver template hooks (`templates/riot/sensor_{bme680,srf04,srf05,button}.c.j2`)

Each driver received three modifications, all guarded by `{% if source_alerts %}` so non-alert peripherals emit byte-identical C to before:

1. Unconditional `#include "mqtt_broker.h"` for `publish_alert` visibility.
2. Function-scope `static uint64_t last_fire_<c_safe_name> = 0;` declarations near the other `_thread` locals.
3. Per-alert cooldown gate inside the success branch (after data is read, before the JSON publish path):

```c
{% if source_alerts %}
    /* ALERT triggers — evaluated on every successful read,
       independent of sampling mode. */
    uint64_t _now_sec = xtimer_now_usec64() / 1000000ULL;
{% for a in source_alerts %}
    if ({{ a.condition_c }}) {
        if ((_now_sec - last_fire_{{ a.c_safe_name }}) >= {{ a.cooldown_sec }}ULL) {
            last_fire_{{ a.c_safe_name }} = _now_sec;
{% for act in a.actions %}
            publish_alert("{{ act.payload_c }}", "{{ act.topic }}");
{% endfor %}
        }
    }
{% endfor %}
{% endif %}
```

`sensor_button.c.j2` wraps the block in its own scope `{ … }` so `_now_sec` does not collide with adjacent locals, and places the block **before** the `if (state != prev_state)` edge-detection branch — alerts evaluate on every sample, not only on transitions.

### 5.7 Phase 2 effort (actual)

~570 LOC across grammar (1), .hwd files (8), validator (1), codegen (2), templates (6), example (1), tests (1), CI (1). Shipped in three atomic commits per the Phase 1 pattern.

---

## 6. Test Strategy

1. **Existing `test_rpi_codegen_syntax.py`** already runs `ast.parse` + `py_compile` on every example. Will catch any broken alert emission.
2. **New `test_rpi_alerts_emission.py`** — for each example with ALERT, parametrize:
   - assert generated file contains `AlertTrigger(name="<alert_name>"`
   - assert generated file contains the threshold value (e.g., `> 37.5`)
   - assert action publisher uses correct broker host
3. **New `test_alert_runtime.py`** — import `alerts.py` directly, instantiate `AlertTrigger`, feed mock data, assert action callbacks fire / don't fire / honor cooldown.
4. **RIOT** — `tests/test_riot_alerts_emission.py` runs string assertions on generated `sensor_bme680_0.c` (mqtt_broker.h include, `last_fire_<name>` statics, SCALE arithmetic, `publish_alert` call with C-escaped payload, `xtimer_now_usec64()` cooldown gate). The `wemos_bme680_alert` entry in the CI matrix runs `./build_docker.sh` against a real RIOT toolchain to prove the emitted C compiles and links against `paho_mqtt`.

---

## 7. Migration & Compatibility

- **Backward compatible:** examples without ALERT generate identical code to before (the alerts list will be empty in the template).
- **Forward compatible:** the small DSL extension for RIOT property typing (Section 5.4) is opt-in until at least one alert references a property in that source.
- **Cooldown unit `hz`** — currently parsed but semantically wrong for a cooldown duration. Action: emit a deprecation warning at codegen, default to 1.0 sec, file an issue to remove from grammar in next major.

---

## 8. Open Questions

1. **Should ACTIVATE-target accept a payload?** Today `ACTIVATE StatusLed` carries no data. Reasonable defaults: actuators with a `command` field receive `{"command": "on"}`; LEDs receive `{"value": 1}`. Or: extend grammar to `ACTIVATE Target WITH {"key": value}`. Recommend deferring to a follow-up.
2. **Alert message schema** — generate a typed `AlertMessage` (matches existing pattern for sensor data) or use bare `dict`? Recommend typed.
3. **RIOT property→struct contract** — is the small `.hwd` DSL extension acceptable, or do we want a different mechanism (e.g., per-peripheral property-list file)?
4. **Threshold comparison with mismatched units** — `WHEN temperature > 37.5 celsius` vs sensor reports temperature in `fahrenheit`. Out of scope for this round; reject at validation as a follow-up.

---

## 9. Recommended Sequence

1. **Phase 1 (RPi only, SHIPPED):** Sections 4.1–4.5 + tests in Section 6 #1-3. Commits `6b94ac8`, `632e749`, `eb98f16`.
2. **Phase 2 (RIOT, SHIPPED):** PROPERTIES grammar + validator + per-driver inline injection + `publish_alert` wrapper + `[Safety-Alert-RiotMultiBroker]` validator warning + CI compile gate. See Section 5.
3. **Phase 3 (future polish):** Address Open Questions 1, 2, 4. Multi-broker RIOT support would require a runtime refactor (per-broker `MQTTClient` instances) — deferred until a use case justifies the cost.
