# Broker Codegen Audit — AMQP and Redis Support

**Author:** T39 (Wave 5)
**Date:** 2026-06-26
**Status:** Audit complete; minimal `get_broker_config()` refactor needed before T40-T45.

## 1. Current State (MQTT-only)

The `BaseCodeGenerator.get_broker_config()` method and all per-backend
broker handling are MQTT-only:

| Method | Location | MQTT-only? |
|--------|----------|------------|
| `get_broker_config()` | `base_generator.py:38-67` | **Yes** — raises `TypeError` on non-MQTT |
| `_broker_to_cfg()` | `m2t_rpi.py:182-193` | **Yes** — MQTT field set only |
| `get_broker_config()` consumer | `m2t_riot.py:76-156` | **Yes** — passes straight to `mqtt_broker.c.j2` |
| `_collect_mqtt_brokers()` | `m2t_zephyr.py:246-281` | **Yes** — name test `!= "MQTTBroker"` skips AMQP/Redis |

The grammar (`communication.tx`) already supports three broker types:

- **AMQP**: host, port, vhost, topicExchange, rpcExchange, ssl, auth.{username,password,key}
- **MQTT**: host, port, ssl, basePath, webPath, webPort, auth.{username,password,key}
- **Redis**: host, port, db, ssl, auth.{username,password,key}

The grammar is ready; the codegen is not.

## 2. Per-Broker Field Requirements

### AMQP (RabbitMQ semantics)
- **Required**: host, port, vhost, exchange (topic/rpc), routing_key
- **Optional**: ssl, auth.{username,password,key}
- **Library (RPi)**: `pika>=1.3.0` (BlockingConnection)
- **Library (RIOT)**: native `amqp` module (C client) or fallback to TCP+manual AMQP frame encode
- **Library (Zephyr)**: native `mqtt` does not cover AMQP; out-of-tree binding or stub scaffold
- **Publish semantics**: `basic_publish(exchange=..., routing_key=..., body=...)` on a `BlockingConnection.channel()`

### Redis (Pub/Sub)
- **Required**: host, port, db
- **Optional**: ssl, auth.{username,password,key}
- **Library (RPi)**: `redis>=5.0` (redis-py, `client.pubsub().subscribe(channel)` + `client.publish(channel, msg)`)
- **Library (RIOT)**: native `sock` module + manual RESP protocol encoding
- **Library (Zephyr)**: native `net` socket + manual RESP; no upstream Redis binding
- **Publish semantics**: `PUBLISH <channel> <body>` (one-shot command)

### MQTT (already supported)
- **Required**: host, port
- **Optional**: ssl, basePath, webPath, webPort, auth.{username,password,key}
- **Library (RPi)**: `paho-mqtt>=1.6.0`
- **Library (RIOT)**: native `mqtt` module (emC)
- **Library (Zephyr)**: native `mqtt` library (`CONFIG_MQTT_LIB=y`)
- **Publish semantics**: `client.publish(topic, payload)`

## 3. Required Changes

### 3.1 Refactor `BaseCodeGenerator.get_broker_config()` (T39)

Replace the current implementation with a broker-type-dispatching version.
The new contract:

```python
def get_broker_config(self, broker: Any = None) -> Dict[str, Any]:
    """Return a broker-type-keyed config dict.

    Returns a dict with a 'kind' field ('amqp' | 'mqtt' | 'redis') plus
    all relevant fields. Backward compatible: when called with no args
    it returns the default broker's config (legacy MQTT-only callers).
    """
    if broker is None:
        broker = self.device_model.broker
    if broker is None:
        return {}
    kind = type(broker).__name__.removesuffix("Broker").lower()
    if kind not in ("amqp", "mqtt", "redis"):
        kind = "unknown"
    cfg = {"kind": kind, "host": broker.host, "port": broker.port}
    # common optional fields
    cfg["ssl"] = getattr(broker, "ssl", False)
    auth = getattr(broker, "auth", None)
    if auth:
        cfg["username"] = getattr(auth, "username", "") or ""
        cfg["password"] = getattr(auth, "password", "") or ""
        cfg["auth_key"] = getattr(auth, "key", "") or ""
    # per-broker optional fields
    if kind == "amqp":
        cfg["vhost"] = getattr(broker, "vhost", "/")
        cfg["topic_exchange"] = getattr(broker, "topicE", "")
        cfg["rpc_exchange"] = getattr(broker, "rpcE", "")
    elif kind == "mqtt":
        cfg["base_path"] = getattr(broker, "basePath", "")
        cfg["web_path"] = getattr(broker, "webPath", "")
        cfg["web_port"] = getattr(broker, "webPort", 0)
    elif kind == "redis":
        cfg["db"] = getattr(broker, "db", 0)
    return cfg
```

The existing `get_broker_config()` (no-arg) form must keep returning a
dict with `host`, `port`, `ssl`, `username`, `password` keys (the legacy
4-tuple) so RIOT and Zephyr backends that pass the result into
`mqtt_broker.c.j2` / `prj.conf.j2` continue to work for the MQTT case.
The new `kind` key is **additive** and is ignored by those templates.

### 3.2 Per-Backend Helper (T40-T45)

Each backend adds:

1. A broker-aware `_collect_brokers()` method that mirrors
   `_collect_mqtt_brokers()` but emits per-broker-kind descriptors.
2. A `get_broker_library_hint(broker)` method that returns
   `'pika' | 'paho-mqtt' | 'redis'` for RPi requirements.txt.j2.
3. A guard in the broker emit step: `if broker.kind != 'mqtt': skip_mqtt_template()`
   so the per-backend AMQP/Redis templates can take over.

### 3.3 Templates Needed

| Backend | AMQP | Redis | MQTT (existing) |
|---------|------|-------|-----------------|
| RPi | `templates/rpi/amqp_broker.py.j2` | `templates/rpi/redis_broker.py.j2` | `templates/rpi/mqtt_broker.py.j2` |
| RIOT | `templates/riot/amqp_broker.c.j2` | `templates/riot/redis_broker.c.j2` | `templates/riot/mqtt_broker.c.j2` |
| Zephyr | `templates/zephyr/amqp_broker.c.j2` | `templates/zephyr/redis_broker.c.j2` | `templates/zephyr/_APP_SRC_MAIN_C` (in m2t_zephyr.py) |

The MQTT templates stay unchanged; AMQP/Redis are new siblings.

## 4. Multi-Broker Semantics (RPi only)

- RPi: supports multi-broker (each broker gets its own connection)
- RIOT: **single** MQTT client (`PER_OS_CAPABILITIES["riotos"]["multi_broker"] = False`)
- Zephyr: forward-declared multi-broker (`PER_OS_CAPABILITIES["zephyr"]["multi_broker"] = True`)

For RIOT, AMQP/Redis codegen must downgrade to the default broker and
log a warning (parallel to the existing MQTT multi-broker warning in
`m2t_riot.py:341-347`).

## 5. Future Work

- Broker-kind-conditional ALERT/PUBLISH: when an ALERT targets a Redis
  broker, the publish call should be `client.publish(channel, body)`, not
  the MQTT `client.publish(topic, payload)`. This is a per-template
  dispatch that T40-T45 will need to handle.
- Broker TLS: `ssl=true` requires an additional dependency (e.g.
  `paho-mqtt[tls]`, `pika[ssl]`). Not gated by T39-T45 but tracked for
  a future task.

## 6. Conclusion

The audit identifies a single shared change (T39) — refactor
`get_broker_config()` to emit a `kind` key alongside the legacy
4-tuple. After that, T40-T45 can implement AMQP and Redis codegen
per backend without further shared code changes.
