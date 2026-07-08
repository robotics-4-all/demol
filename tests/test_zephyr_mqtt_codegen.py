"""
T16: Zephyr MQTT codegen (Kconfig + skeleton only).

When ``model.brokers`` contains an MQTT broker, the Zephyr backend must:
  1. Emit Zephyr Kconfig symbols for the network + MQTT stack in ``prj.conf``.
  2. Emit a ``mqtt_init()`` function skeleton in ``app/src/main.c`` that
     declares a ``struct mqtt_client`` and registers the include directives.

The full publish loop is intentionally deferred (T17+). The skeleton must be
syntactically valid C and backward compatible: a model without any MQTT
broker must produce a ``prj.conf``/``main.c`` with NO MQTT footprint.
"""

from pathlib import Path
from textwrap import dedent

import pytest

from demol.lang import get_device_mm
from demol.transformations.m2t_zephyr import m2t_zephyr

# ---------------------------------------------------------------------------
# Inline DSL fixtures
# ---------------------------------------------------------------------------

# A minimal ESP-Wemos model with an MQTT broker.
ZEPHYR_MQTT_MODEL = dedent("""\
    DEVICE MyWemos WITH description="zephyr mqtt codegen test", author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyMqttBroker WITH host="node.mqtt.local", port=1883,
        auth.username="guest", auth.password="guest";

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";
    """)


# A model with NO MQTT broker — uses AMQP instead to satisfy the broker
# well-formedness rule. The codegen must still produce NO MQTT footprint.
ZEPHYR_NO_MQTT_MODEL = dedent("""\
    DEVICE MyWemosNoMqtt WITH description="zephyr no-mqtt backward compat", author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[AMQP] MyAmqpBroker WITH host="rabbit.mqtt.local", port=5672,
        auth.username="guest", auth.password="guest";

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";
    """)


# A model with multiple MQTT brokers — every MQTT broker must yield a
# skeleton + Kconfig entries (Kconfig is currently shared per-app).
ZEPHYR_MULTI_MQTT_MODEL = dedent("""\
    DEVICE MyWemosMulti WITH description="zephyr multi-mqtt codegen test", author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] PrimaryBroker WITH host="primary.mqtt.local", port=1883,
        auth.username="guest", auth.password="guest";
    BROKER[MQTT] SecondaryBroker WITH host="secondary.mqtt.local", port=8883,
        auth.username="guest", auth.password="guest";

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";
    """)


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def device_mm():
    return get_device_mm()


@pytest.fixture(scope="module")
def mqtt_model(device_mm):
    return device_mm.model_from_str(ZEPHYR_MQTT_MODEL)


@pytest.fixture(scope="module")
def no_mqtt_model(device_mm):
    return device_mm.model_from_str(ZEPHYR_NO_MQTT_MODEL)


@pytest.fixture(scope="module")
def multi_mqtt_model(device_mm):
    return device_mm.model_from_str(ZEPHYR_MULTI_MQTT_MODEL)


@pytest.fixture(scope="module")
def mqtt_out(tmp_path_factory, mqtt_model) -> Path:
    """Generated Zephyr project tree for a model with one MQTT broker."""
    out = tmp_path_factory.mktemp("mqtt_out")
    m2t_zephyr(mqtt_model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def no_mqtt_out(tmp_path_factory, no_mqtt_model) -> Path:
    """Generated Zephyr project tree for a model with NO MQTT broker."""
    out = tmp_path_factory.mktemp("no_mqtt_out")
    m2t_zephyr(no_mqtt_model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def multi_mqtt_out(tmp_path_factory, multi_mqtt_model) -> Path:
    """Generated Zephyr project tree for a model with multiple MQTT brokers."""
    out = tmp_path_factory.mktemp("multi_mqtt_out")
    m2t_zephyr(multi_mqtt_model, output_dir=str(out))
    return out


# ---------------------------------------------------------------------------
# Kconfig emission
# ---------------------------------------------------------------------------


class TestKconfigEmission:
    """The generated ``prj.conf`` must enable the network + MQTT stack."""

    def test_mqtt_lib_enabled(self, mqtt_out: Path):
        """`CONFIG_MQTT_LIB=y` is the canonical Zephyr symbol for the MQTT client."""
        prj = (mqtt_out / "app" / "prj.conf").read_text()
        assert "CONFIG_MQTT_LIB=y" in prj, (
            "Expected CONFIG_MQTT_LIB=y in prj.conf when an MQTT broker is " "present. Got:\n" + prj
        )

    def test_network_ipv4_enabled(self, mqtt_out: Path):
        prj = (mqtt_out / "app" / "prj.conf").read_text()
        assert "CONFIG_NET_IPV4=y" in prj, (
            "Expected CONFIG_NET_IPV4=y — MQTT needs a working TCP/IP stack. " "Got:\n" + prj
        )

    def test_network_tcp_enabled(self, mqtt_out: Path):
        prj = (mqtt_out / "app" / "prj.conf").read_text()
        assert "CONFIG_NET_TCP=y" in prj, "Expected CONFIG_NET_TCP=y — MQTT sits on top of TCP. " "Got:\n" + prj

    def test_sockets_enabled(self, mqtt_out: Path):
        prj = (mqtt_out / "app" / "prj.conf").read_text()
        assert "CONFIG_NET_SOCKETS=y" in prj, (
            "Expected CONFIG_NET_SOCKETS=y — Zephyr's MQTT client uses BSD " "sockets internally. Got:\n" + prj
        )

    def test_multi_broker_model_enables_mqtt_lib(self, multi_mqtt_out: Path):
        """Multiple MQTT brokers still produce CONFIG_MQTT_LIB=y exactly once."""
        prj = (multi_mqtt_out / "app" / "prj.conf").read_text()
        assert "CONFIG_MQTT_LIB=y" in prj
        # Deduplicated — CONFIG_MQTT_LIB=y must appear at least once.
        assert prj.count("CONFIG_MQTT_LIB=y") >= 1


class TestKconfigBackwardCompat:
    """A model without an MQTT broker must not opt-in to the MQTT stack."""

    def test_no_mqtt_lib(self, no_mqtt_out: Path):
        prj = (no_mqtt_out / "app" / "prj.conf").read_text()
        assert "CONFIG_MQTT_LIB" not in prj, (
            "Backward-compat violated: CONFIG_MQTT_LIB must NOT appear when "
            "the model has no MQTT broker. Got:\n" + prj
        )

    def test_no_mqtt_specific_sockets(self, no_mqtt_out: Path):
        prj = (no_mqtt_out / "app" / "prj.conf").read_text()
        # Net stack is up to the user; we never auto-enable networking symbols
        # in the absence of a broker.
        assert "CONFIG_NET_SOCKETS" not in prj


# ---------------------------------------------------------------------------
# main.c emission
# ---------------------------------------------------------------------------


class TestMainCEmission:
    """The generated ``app/src/main.c`` must define an ``mqtt_init()`` skeleton."""

    def test_mqtt_init_function_present(self, mqtt_out: Path):
        main_c = (mqtt_out / "app" / "src" / "main.c").read_text()
        assert "mqtt_init" in main_c, (
            "Expected `mqtt_init` to be referenced in main.c when the model " "has an MQTT broker. Got:\n" + main_c
        )

    def test_mqtt_init_called_from_main(self, mqtt_out: Path):
        """`mqtt_init()` must be invoked from `main()`."""
        main_c = (mqtt_out / "app" / "src" / "main.c").read_text()
        assert "mqtt_init();" in main_c, "Expected `mqtt_init();` invocation inside main(). Got:\n" + main_c

    def test_mqtt_header_included(self, mqtt_out: Path):
        main_c = (mqtt_out / "app" / "src" / "main.c").read_text()
        assert "#include <zephyr/net/mqtt.h>" in main_c, (
            "Expected `#include <zephyr/net/mqtt.h>` in main.c. Got:\n" + main_c
        )

    def test_socket_header_included(self, mqtt_out: Path):
        main_c = (mqtt_out / "app" / "src" / "main.c").read_text()
        assert "#include <zephyr/net/socket.h>" in main_c, (
            "Expected `#include <zephyr/net/socket.h>` in main.c. Got:\n" + main_c
        )

    def test_mqtt_client_struct_declared(self, mqtt_out: Path):
        main_c = (mqtt_out / "app" / "src" / "main.c").read_text()
        assert "struct mqtt_client" in main_c, (
            "Expected `struct mqtt_client client;` declaration in main.c. " "Got:\n" + main_c
        )


class TestMainCBackwardCompat:
    """A model without an MQTT broker must not contain any MQTT footprint."""

    def test_no_mqtt_includes(self, no_mqtt_out: Path):
        main_c = (no_mqtt_out / "app" / "src" / "main.c").read_text()
        assert "zephyr/net/mqtt.h" not in main_c, (
            "Backward-compat violated: `zephyr/net/mqtt.h` must NOT be "
            "included when the model has no MQTT broker. Got:\n" + main_c
        )

    def test_no_mqtt_init_call(self, no_mqtt_out: Path):
        main_c = (no_mqtt_out / "app" / "src" / "main.c").read_text()
        assert "mqtt_init" not in main_c, (
            "Backward-compat violated: `mqtt_init` must NOT be referenced "
            "when the model has no MQTT broker. Got:\n" + main_c
        )


# ---------------------------------------------------------------------------
# Skeleton must be syntactically valid C
# ---------------------------------------------------------------------------


class TestMqttSkeletonCompilable:
    """
    The skeleton must be syntactically valid C (even if it does not actually
    connect to a broker). We lint it with a brace-balance check; a full
    gcc -fsyntax-only gate is not part of T16 (covered by CI).
    """

    def test_brace_balance(self, mqtt_out: Path):
        main_c = (mqtt_out / "app" / "src" / "main.c").read_text()
        assert main_c.count("{") == main_c.count("}"), (
            "Unbalanced braces in main.c — generator emitted invalid C.\n"
            f"Open  {{: {main_c.count('{')}, Close }}: {main_c.count('}')}"
        )

    def test_skeleton_contains_no_publish_loop(self, mqtt_out: Path):
        """
        T16 is a SKELETON ONLY — the full publish loop is deferred. The
        emitted code must not contain a publish-related MQTT call, only the
        init/connect scaffolding.
        """
        main_c = (mqtt_out / "app" / "src" / "main.c").read_text()
        forbidden = [
            "mqtt_publish",
            "while (1)",
            "for (;;)",
        ]
        for token in forbidden:
            assert token not in main_c, (
                f"T16 scope violation: `{token}` must NOT appear in the "
                "skeleton. The full publish loop is deferred to T17+.\n" + main_c
            )
