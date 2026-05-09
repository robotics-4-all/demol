"""String-level emission tests for ALERT codegen on the RPi target.

Covers the contract documented in ``docs/design-alerts-codegen.md``:
- ``alerts.py`` runtime helper is emitted for every device
- Sensor nodes that own one or more alerts import and instantiate
  ``AlertTrigger`` and call ``evaluate`` from the run loop
- VIA broker routing produces a per-broker ``Node`` and publisher map
- ACTIVATE actions resolve to the target peripheral's CONNECT topic
- Sensor nodes with no alerts on them stay clean (no alert-related code)
"""

from pathlib import Path

import pytest

from demol.transformations.m2t_rpi import RPiCodeGenerator


@pytest.fixture(scope="module")
def health_monitor_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("rpi_health_monitor")
    model = device_mm.model_from_file("examples/rpi/rpi_health_monitor.dev")
    RPiCodeGenerator(model, out).generate()
    return out


@pytest.fixture(scope="module")
def alert_triggers_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("rpi_alert_triggers")
    model = device_mm.model_from_file("examples/rpi/rpi_alert_triggers.dev")
    RPiCodeGenerator(model, out).generate()
    return out


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class TestAlertsRuntimeEmission:
    def test_alerts_module_emitted(self, health_monitor_out):
        assert (health_monitor_out / "alerts.py").is_file()

    def test_alerts_module_exports(self, health_monitor_out):
        body = _read(health_monitor_out / "alerts.py")
        assert "class AlertTrigger" in body
        assert "def evaluate" in body
        assert "make_broker_node" in body
        assert "make_publisher" in body


class TestSensorNodeAlertsHookup:
    def test_irthermometer_imports_alert_trigger(self, health_monitor_out):
        body = _read(health_monitor_out / "irthermometer_node.py")
        assert "from .alerts import AlertTrigger" in body

    def test_irthermometer_defines_fever_alert(self, health_monitor_out):
        body = _read(health_monitor_out / "irthermometer_node.py")
        assert "_cond_fever_alert" in body
        assert "AlertTrigger(" in body
        assert 'name="fever_alert"' in body

    def test_irthermometer_routes_via_health_gateway(self, health_monitor_out):
        body = _read(health_monitor_out / "irthermometer_node.py")
        assert 'self._alert_brokers["HealthGateway"]' in body
        assert 'topic="health/alerts/fever"' in body

    def test_run_loop_evaluates_alerts(self, health_monitor_out):
        body = _read(health_monitor_out / "irthermometer_node.py")
        assert "for _alert in self.alerts" in body
        assert "_alert.evaluate(_data)" in body

    def test_condition_uses_property_dict_lookup(self, health_monitor_out):
        body = _read(health_monitor_out / "irthermometer_node.py")
        # The condition must be a Python expression that reads the data dict
        assert "data.get('object_temperature')" in body
        assert "data['object_temperature']" in body


class TestActuatorNodesUnchanged:
    def test_status_led_node_has_no_alert_code(self, health_monitor_out):
        body = _read(health_monitor_out / "statusled_node.py")
        assert "AlertTrigger" not in body
        assert "_alert_brokers" not in body


class TestActivateActionRouting:
    def test_activate_resolves_to_target_topic(self, alert_triggers_out):
        body = _read(alert_triggers_out / "envsensor_node.py")
        # AlarmBuzzer is connected at topic "actuators/alarm"
        assert 'topic="actuators/alarm"' in body
        # StatusLed is connected at topic "actuators/status"
        assert 'topic="actuators/status"' in body

    def test_multiple_actions_per_alert_indexed(self, alert_triggers_out):
        body = _read(alert_triggers_out / "envsensor_node.py")
        # gas_leak has 3 actions: PUBLISH + 2 ACTIVATE
        assert '("gas_leak", 0)' in body
        assert '("gas_leak", 1)' in body
        assert '("gas_leak", 2)' in body
