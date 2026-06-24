"""Per-OS capability table tests for AlertValidator.

Verifies the multi-broker warning contract of
``demol.lang.semantics.validators.alert``:

* raspbian models with a non-default ``VIA`` broker emit **no** warning
  (raspbian supports multi-broker routing natively)
* riotos models with a non-default ``VIA`` broker **do** emit
  ``[Safety-Alert-RiotMultiBroker]`` (RIOT firmware ships a single
  MQTTClient; the rule name is preserved for backward compatibility)
* zephyr models with a non-default ``VIA`` broker emit **no** warning
  (zephyr is forward-declared to support multi-broker routing)

The capability table is consulted via
:func:`demol.lang.semantics.validators.alert._supports_multi_broker`,
and unknown OSes default to ``True`` (multi-broker allowed) so adding a
new target can never silently strip multi-broker routing.
"""

import warnings

import pytest

from demol.lang.semantics.validators import alert as alert_module
from demol.lang.semantics.validators.alert import (
    PER_OS_CAPABILITIES,
    _supports_multi_broker,
)

# Two brokers declared in source-order: ``Local`` is the default (first
# in source), ``Cloud`` is non-default. Using ``VIA Cloud`` therefore
# always exercises the non-default-VIA branch of AlertValidator.
PREAMBLE = """
DEVICE TestAlerts WITH description="Test", author="Test", os={os};
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];

NETWORK[WiFi] WITH ssid="test", password="test123";
BROKER[MQTT] Local WITH host="localhost", port=1883;
BROKER[MQTT] Cloud WITH host="mqtt.test.com", port=1883,
    auth.username="user", auth.password="pass";

CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";

ALERT frost ON EnvSensor WHEN
    temperature < 2
    THEN
    PUBLISH "alerts/frost" VIA Cloud;
"""


@pytest.mark.parametrize(
    "os_key,expects_warning",
    [
        ("raspbian", False),
        ("riotos", True),
        ("zephyr", False),
    ],
    ids=["raspbian-no-warning", "riotos-emits-warning", "zephyr-no-warning"],
)
def test_alert_validator_per_os_multi_broker_warning(device_mm, os_key, expects_warning):
    model_str = PREAMBLE.format(os=os_key)
    if expects_warning:
        with pytest.warns(UserWarning, match=r"\[Safety-Alert-RiotMultiBroker\]"):
            device_mm.model_from_str(model_str)
    else:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            device_mm.model_from_str(model_str)
        rule_warnings = [w for w in caught if "Safety-Alert-RiotMultiBroker" in str(w.message)]
        assert rule_warnings == [], (
            f"[{os_key}] expected no [Safety-Alert-RiotMultiBroker] warning, "
            f"got: {[str(w.message) for w in rule_warnings]}"
        )


def test_per_os_capabilities_table_shape():
    assert "raspbian" in PER_OS_CAPABILITIES
    assert "riotos" in PER_OS_CAPABILITIES
    assert "zephyr" in PER_OS_CAPABILITIES


def test_per_os_capabilities_values():
    assert PER_OS_CAPABILITIES["raspbian"]["multi_broker"] is True
    assert PER_OS_CAPABILITIES["riotos"]["multi_broker"] is False
    assert PER_OS_CAPABILITIES["zephyr"]["multi_broker"] is True


def test_supports_multi_broker_known_os():
    assert _supports_multi_broker("raspbian") is True
    assert _supports_multi_broker("riotos") is False
    assert _supports_multi_broker("zephyr") is True


def test_supports_multi_broker_unknown_os_defaults_true():
    """Adding a new target OS must never silently strip multi-broker routing."""
    assert _supports_multi_broker("freertos") is True
    assert _supports_multi_broker("contiki") is True
    assert _supports_multi_broker("") is True


def test_alert_module_exports_capability_symbols():
    assert hasattr(alert_module, "PER_OS_CAPABILITIES")
    assert hasattr(alert_module, "_supports_multi_broker")
