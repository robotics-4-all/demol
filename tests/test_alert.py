"""Tests for ALERT trigger feature."""

import pytest
import warnings
from textx import TextXSemanticError


@pytest.fixture(scope="session")
def device_mm():
    from demol.lang import get_device_mm

    return get_device_mm()


@pytest.fixture(scope="session")
def device_mm_skip():
    from demol.lang import get_device_mm

    return get_device_mm(skip_semantics=True)


VALID_PREAMBLE = """
DEVICE TestAlerts WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];
USE BuzzerGeneric[Alarm];
USE LedGeneric[StatusLed];

NETWORK[WiFi] WITH ssid="test", password="test123";
BROKER[MQTT] Cloud WITH host="mqtt.test.com", port=1883,
    auth.username="user", auth.password="pass";
BROKER[MQTT] Local WITH host="localhost", port=1883;

CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";

CONNECT Alarm WITH
    POWER gnd -- GND_2
    DATA gpio[mode="output"] vin -- GPIO22
    @ "actuators/alarm";

CONNECT StatusLed WITH
    POWER gnd -- GND_3, vcc -- power_3v3_a
    DATA gpio[mode="output"] vin -- GPIO17
    @ "actuators/led";
"""


def test_alert_single_condition(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT frost ON EnvSensor WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/frost";
""")
    assert len(model.alerts) == 1
    alert = model.alerts[0]
    assert alert.name == "frost"
    cond = alert.condition
    assert cond.left.property == "temperature"
    assert cond.left.op == "<"
    assert cond.left.value == 2


def test_alert_compound_condition_and(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT heat ON EnvSensor WHEN
    temperature > 40 && humidity < 20
    THEN
    PUBLISH "alerts/heat";
""")
    alert = model.alerts[0]
    cond = alert.condition
    assert cond.left.property == "temperature"
    assert cond.left.op == ">"
    assert cond.left.value == 40
    assert cond.op == "&&"
    assert cond.right.left.property == "humidity"
    assert cond.right.left.op == "<"
    assert cond.right.left.value == 20


def test_alert_compound_condition_or(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT extreme ON EnvSensor WHEN
    temperature > 50 || temperature < -10
    THEN
    PUBLISH "alerts/extreme";
""")
    alert = model.alerts[0]
    cond = alert.condition
    assert cond.op == "||"


def test_alert_publish_with_via(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT frost ON EnvSensor WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/frost" VIA Cloud;
""")
    alert = model.alerts[0]
    action = alert.actions[0]
    assert action.__class__.__name__ == "AlertPublish"
    assert action.topic == "alerts/frost"
    assert action.via == "Cloud"


def test_alert_activate_actuator(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT frost ON EnvSensor WHEN
    temperature < 2
    THEN
    ACTIVATE Alarm;
""")
    alert = model.alerts[0]
    action = alert.actions[0]
    assert action.__class__.__name__ == "AlertActivate"
    assert action.target.name == "Alarm"


def test_alert_multiple_actions(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT frost ON EnvSensor WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/frost" VIA Cloud
    ACTIVATE Alarm
    ACTIVATE StatusLed;
""")
    alert = model.alerts[0]
    assert len(alert.actions) == 3
    assert alert.actions[0].__class__.__name__ == "AlertPublish"
    assert alert.actions[1].__class__.__name__ == "AlertActivate"
    assert alert.actions[2].__class__.__name__ == "AlertActivate"


def test_alert_with_cooldown(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT frost ON EnvSensor WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/frost"
    COOLDOWN 60 hz;
""")
    alert = model.alerts[0]
    assert alert.cooldown == 60
    assert alert.cooldown_unit == "hz"


def test_alert_without_cooldown(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT frost ON EnvSensor WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/frost";
""")
    alert = model.alerts[0]
    assert alert.cooldown == 0.0


def test_alert_multiple_alerts(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT frost ON EnvSensor WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/frost";

ALERT heat ON EnvSensor WHEN
    temperature > 40
    THEN
    PUBLISH "alerts/heat";
""")
    assert len(model.alerts) == 2
    assert model.alerts[0].name == "frost"
    assert model.alerts[1].name == "heat"


def test_alert_condition_with_unit(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT power_high ON EnvSensor WHEN
    power > 500 mW
    THEN
    PUBLISH "alerts/power";
""")
    alert = model.alerts[0]
    comp = alert.condition.left
    assert comp.value == 500
    assert comp.unit == "mW"


def test_alert_duplicate_names_error(device_mm):
    with pytest.raises(TextXSemanticError, match="Duplicate alert name"):
        device_mm.model_from_str(VALID_PREAMBLE + """
ALERT frost ON EnvSensor WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/frost1";

ALERT frost ON EnvSensor WHEN
    temperature < 5
    THEN
    PUBLISH "alerts/frost2";
""")


def test_alert_source_is_actuator_error(device_mm):
    with pytest.raises(TextXSemanticError, match="is an actuator"):
        device_mm.model_from_str(VALID_PREAMBLE + """
ALERT bad ON Alarm WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/bad";
""")


def test_alert_activate_sensor_error(device_mm):
    with pytest.raises(TextXSemanticError, match="is a sensor"):
        device_mm.model_from_str(VALID_PREAMBLE + """
ALERT bad ON EnvSensor WHEN
    temperature < 2
    THEN
    ACTIVATE EnvSensor;
""")


def test_alert_via_unknown_broker_error(device_mm):
    with pytest.raises(TextXSemanticError, match="no broker with that name"):
        device_mm.model_from_str(VALID_PREAMBLE + """
ALERT frost ON EnvSensor WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/frost" VIA NonExistent;
""")


def test_alert_valid_full_model(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT frost ON EnvSensor WHEN
    temperature < 2 && humidity > 80
    THEN
    PUBLISH "alerts/frost" VIA Cloud
    ACTIVATE Alarm
    COOLDOWN 30 hz;

ALERT heat ON EnvSensor WHEN
    temperature > 45
    THEN
    PUBLISH "alerts/heat" VIA Local
    ACTIVATE StatusLed;
""")
    assert len(model.alerts) == 2
    frost = model.alerts[0]
    assert frost.name == "frost"
    assert len(frost.actions) == 2
    assert frost.cooldown == 30

    heat = model.alerts[1]
    assert heat.name == "heat"
    assert len(heat.actions) == 2


def test_alert_no_alerts_is_valid(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE)
    assert len(model.alerts) == 0


def test_alert_triple_condition(device_mm_skip):
    model = device_mm_skip.model_from_str(VALID_PREAMBLE + """
ALERT complex ON EnvSensor WHEN
    temperature > 30 && humidity > 70 && pressure < 1000
    THEN
    PUBLISH "alerts/complex";
""")
    alert = model.alerts[0]
    cond = alert.condition
    assert cond.left.property == "temperature"
    assert cond.op == "&&"
    inner = cond.right
    assert inner.left.property == "humidity"
    assert inner.op == "&&"
    assert inner.right.left.property == "pressure"
