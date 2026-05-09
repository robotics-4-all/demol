"""String-level emission tests for ALERT codegen on the RiotOS target.

Covers the contract documented in ``docs/design-alerts-codegen.md`` Phase 2:
- ``publish_alert()`` wrapper is emitted into ``main.c`` and declared in ``mqtt_broker.h``
- Sensor drivers that own one or more alerts:
  - include ``mqtt_broker.h`` for the publisher prototype
  - declare per-alert ``static uint64_t last_fire_<name>`` cooldown trackers
  - evaluate the C condition with SCALE-applied integer literals
  - call ``publish_alert(payload, topic)`` inside the cooldown gate
- Sensor drivers without alerts stay clean (no ALERT-related code emitted)

These are pure string assertions on emitted .c content. The CI ``riot-build``
matrix job exercises the actual compile.
"""

from pathlib import Path

import pytest

from demol.transformations.m2t_riot import RiotCodeGenerator


@pytest.fixture(scope="module")
def bme680_alert_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("riot_bme680_alert")
    model = device_mm.model_from_file("examples/esp/wemos_bme680_alert.dev")
    RiotCodeGenerator(model, out).generate()
    return out


@pytest.fixture(scope="module")
def bme680_no_alert_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("riot_bme680_plain")
    model = device_mm.model_from_file("examples/esp/wemos_bme680.dev")
    RiotCodeGenerator(model, out).generate()
    return out


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class TestPublishAlertWrapper:
    def test_main_c_defines_publish_alert(self, bme680_alert_out):
        body = _read(bme680_alert_out / "main.c")
        assert "void publish_alert(char *payload, char *topic)" in body
        assert "mqtt_publish(&client, &network, payload, topic)" in body

    def test_mqtt_broker_h_declares_publish_alert(self, bme680_alert_out):
        body = _read(bme680_alert_out / "mqtt_broker.h")
        assert "void publish_alert(char *payload, char *topic);" in body


class TestDriverAlertEmission:
    def test_driver_includes_mqtt_broker_header(self, bme680_alert_out):
        body = _read(bme680_alert_out / "sensor_bme680_0.c")
        assert '#include "mqtt_broker.h"' in body

    def test_driver_declares_cooldown_statics(self, bme680_alert_out):
        body = _read(bme680_alert_out / "sensor_bme680_0.c")
        assert "static uint64_t last_fire_fever_alert = 0;" in body
        assert "static uint64_t last_fire_humid_alert = 0;" in body

    def test_driver_renders_scaled_integer_conditions(self, bme680_alert_out):
        body = _read(bme680_alert_out / "sensor_bme680_0.c")
        # temperature > 38.5 with SCALE=100 -> 3850
        assert "(data.temperature) > (int64_t)(3850)" in body
        # humidity > 75.0 with SCALE=1000 -> 75000
        assert "(data.humidity) > (int64_t)(75000)" in body

    def test_driver_uses_xtimer_for_cooldown(self, bme680_alert_out):
        body = _read(bme680_alert_out / "sensor_bme680_0.c")
        assert "xtimer_now_usec64() / 1000000ULL" in body

    def test_driver_calls_publish_alert_with_payload_and_topic(self, bme680_alert_out):
        body = _read(bme680_alert_out / "sensor_bme680_0.c")
        assert 'publish_alert("{\\"alert\\":\\"fever_alert\\",\\"source\\":\\"BME\\"}"' in body
        assert '"my_wemos.alerts.fever"' in body
        assert 'publish_alert("{\\"alert\\":\\"humid_alert\\",\\"source\\":\\"BME\\"}"' in body
        assert '"my_wemos.alerts.humidity"' in body

    def test_cooldown_gate_uses_declared_seconds(self, bme680_alert_out):
        body = _read(bme680_alert_out / "sensor_bme680_0.c")
        # Both alerts in the example use COOLDOWN N hz which is coerced to seconds.
        assert "last_fire_fever_alert) >= 60ULL" in body
        assert "last_fire_humid_alert) >= 30ULL" in body


class TestDriverWithoutAlertsStaysClean:
    def test_plain_driver_has_no_alert_code(self, bme680_no_alert_out):
        body = _read(bme680_no_alert_out / "sensor_bme680_0.c")
        assert "last_fire_" not in body
        assert "publish_alert(" not in body
