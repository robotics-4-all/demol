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

## 5. RIOT Implementation Sketch

More invasive — no closures, no dicts of broker configs, must use static structs.

### 5.1 New header pair: `templates/riot/alerts.{c,h}.j2`

```c
typedef bool (*alert_check_fn_t)(const sensor_data_t *data);
typedef void (*alert_action_fn_t)(void);

typedef struct {
    const char *name;
    alert_check_fn_t check;
    alert_action_fn_t *actions;
    size_t actions_count;
    uint32_t cooldown_us;
    uint32_t last_fired_us;
} alert_t;

void alerts_init(alert_t *alerts, size_t count);
void alerts_evaluate(alert_t *alerts, size_t count, const sensor_data_t *data);
```

### 5.2 Per-source alert table emission

In each `sensor_*.c.j2`, after publishing the data:

```c
{% if source_alerts %}
static bool fever_alert_check(const sensor_data_t *d) {
    return d->object_temperature > 37.5f;
}
static void fever_alert_pub_0(void) {
    mqtt_broker_publish(&brk_HealthGateway, "health/alerts/fever",
                        "{\"alert\":\"fever_alert\"}");
}
static void fever_alert_act_0(void) {
    mqtt_broker_publish(&brk_HealthGateway, "health/status",
                        "{\"command\":\"on\"}");
}
static alert_action_fn_t fever_alert_actions[] = { fever_alert_pub_0, fever_alert_act_0 };
static alert_t source_alerts[] = {
    { "fever_alert", fever_alert_check, fever_alert_actions, 2, 60UL * 1000000UL, 0 },
};
{% endif %}
```

### 5.3 Multi-broker brokers

`mqtt_broker.{c,h}` currently exposes one global broker. Refactor to: one `mqtt_broker_t` struct per broker in `main.c`, each peripheral driver passed pointers to the brokers it uses (data broker + alert VIA brokers).

### 5.4 Property→data-struct contract

The biggest RIOT-specific concern: `condition.property = "temperature"` must compile to `data->temperature`. We need a stable, generated `sensor_<peripheral>_data_t` struct that names match the .hwd ATTRIBUTES section. **Today this is informal**. Two options:

A. **Cheap:** declare in each .hwd a `DATA_FIELDS:` section listing names+C types, fail at codegen if alert references unknown field.
B. **Expensive:** introspect existing C drivers via convention. Brittle.

I recommend **(A)** — add a small DSL extension (`PROPERTIES property_name : type, ...` in `.hwd`) and validate at parse time.

### 5.5 Effort estimate

- RPi alone: ~half day (templates + 3 helpers + tests). Low risk.
- RIOT: ~1.5–2 days. Requires DSL extension for property typing. Medium risk.

---

## 6. Test Strategy

1. **Existing `test_rpi_codegen_syntax.py`** already runs `ast.parse` + `py_compile` on every example. Will catch any broken alert emission.
2. **New `test_rpi_alerts_emission.py`** — for each example with ALERT, parametrize:
   - assert generated file contains `AlertTrigger(name="<alert_name>"`
   - assert generated file contains the threshold value (e.g., `> 37.5`)
   - assert action publisher uses correct broker host
3. **New `test_alert_runtime.py`** — import `alerts.py` directly, instantiate `AlertTrigger`, feed mock data, assert action callbacks fire / don't fire / honor cooldown.
4. **RIOT** — extend `test_riot_codegen_syntax.py` analog, but C-level (string assertions only; Docker compile gate catches the rest).

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

1. **Phase 1 (RPi only, half day):** Sections 4.1–4.5 + tests in Section 6 #1-3. Ship.
2. **Phase 2 (RIOT, separate PR):** Add DSL property-type extension + validator → re-emit RIOT drivers with alert tables → CI compile gate proves it.
3. **Phase 3 (polish):** Address Open Questions 1, 2, 4.

This gives a clean, low-blast-radius RPi rollout immediately, and a more deliberate RIOT pass once the DSL story is settled.
