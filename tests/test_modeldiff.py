"""Tests for the model diff engine."""

import os
import tempfile
import pytest
from demol.cli.modeldiff import compute_diff, _diff_dicts

MODEL_A = """\
DEVICE StationA WITH description="Station A", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];
USE BuzzerGeneric[Alarm];

NETWORK[WiFi] WITH ssid="test", password="pass123";
BROKER[MQTT] Cloud WITH host="mqtt.example.com", port=1883,
    auth.username="user", auth.password="pass";

CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";

CONNECT Alarm WITH
    POWER gnd -- GND_2
    DATA gpio[mode="output"] vin -- GPIO22
    @ "actuators/alarm";

SAMPLING EnvSensor WITH rate = 10 hz, mode = continuous;

CONSTRAINT min_sensors: count(SENSOR) >= 1;
"""

MODEL_B = """\
DEVICE StationB WITH description="Station B", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];
USE LedGeneric[StatusLed];

NETWORK[WiFi] WITH ssid="test", password="pass123";
BROKER[MQTT] Cloud WITH host="mqtt.example.com", port=8883,
    auth.username="user", auth.password="pass";
BROKER[MQTT] Local WITH host="localhost", port=1883;

CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env"
    VIA Cloud;

CONNECT StatusLed WITH
    POWER gnd -- GND_3, vcc -- power_3v3_a
    DATA gpio[mode="output"] vin -- GPIO17
    @ "actuators/led";

SAMPLING EnvSensor WITH rate = 5 hz, mode = on_change, threshold = 0.5;

CONSTRAINT min_sensors: count(SENSOR) >= 2;

ALERT heat ON EnvSensor WHEN
    temperature > 40
    THEN
    PUBLISH "alerts/heat";
"""


def _write_tmp(content):
    fd, path = tempfile.mkstemp(suffix=".dev")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


class TestDiffDicts:
    def test_added(self):
        diffs = _diff_dicts("Cat", {}, {"x": {"k": 1}})
        assert len(diffs) == 1
        assert diffs[0][0] == "added"

    def test_removed(self):
        diffs = _diff_dicts("Cat", {"x": {"k": 1}}, {})
        assert len(diffs) == 1
        assert diffs[0][0] == "removed"

    def test_changed(self):
        diffs = _diff_dicts("Cat", {"x": {"k": 1}}, {"x": {"k": 2}})
        assert len(diffs) == 1
        assert diffs[0][0] == "changed"

    def test_identical(self):
        diffs = _diff_dicts("Cat", {"x": {"k": 1}}, {"x": {"k": 1}})
        assert len(diffs) == 0


class TestComputeDiff:
    def test_identical_models(self):
        a = _write_tmp(MODEL_A)
        try:
            diffs = compute_diff(a, a)
            assert len(diffs) == 0
        finally:
            os.unlink(a)

    def test_detects_metadata_change(self):
        a = _write_tmp(MODEL_A)
        b = _write_tmp(MODEL_B)
        try:
            diffs = compute_diff(a, b)
            meta_diffs = [d for d in diffs if d[1] == "Device"]
            assert len(meta_diffs) == 1
            assert meta_diffs[0][0] == "changed"
        finally:
            os.unlink(a)
            os.unlink(b)

    def test_detects_peripheral_add_remove(self):
        a = _write_tmp(MODEL_A)
        b = _write_tmp(MODEL_B)
        try:
            diffs = compute_diff(a, b)
            periph_diffs = [d for d in diffs if d[1] == "Peripheral"]
            removed = [d for d in periph_diffs if d[0] == "removed"]
            added = [d for d in periph_diffs if d[0] == "added"]
            assert any(d[2] == "Alarm" for d in removed)
            assert any(d[2] == "StatusLed" for d in added)
        finally:
            os.unlink(a)
            os.unlink(b)

    def test_detects_broker_changes(self):
        a = _write_tmp(MODEL_A)
        b = _write_tmp(MODEL_B)
        try:
            diffs = compute_diff(a, b)
            broker_diffs = [d for d in diffs if d[1] == "Broker"]
            assert len(broker_diffs) >= 1
            added_brokers = [d for d in broker_diffs if d[0] == "added"]
            assert any(d[2] == "Local" for d in added_brokers)
        finally:
            os.unlink(a)
            os.unlink(b)

    def test_detects_sampling_change(self):
        a = _write_tmp(MODEL_A)
        b = _write_tmp(MODEL_B)
        try:
            diffs = compute_diff(a, b)
            sampling_diffs = [d for d in diffs if d[1] == "Sampling"]
            assert len(sampling_diffs) >= 1
            assert sampling_diffs[0][0] == "changed"
        finally:
            os.unlink(a)
            os.unlink(b)

    def test_detects_alert_addition(self):
        a = _write_tmp(MODEL_A)
        b = _write_tmp(MODEL_B)
        try:
            diffs = compute_diff(a, b)
            alert_diffs = [d for d in diffs if d[1] == "Alert"]
            assert len(alert_diffs) == 1
            assert alert_diffs[0][0] == "added"
            assert alert_diffs[0][2] == "heat"
        finally:
            os.unlink(a)
            os.unlink(b)

    def test_detects_constraint_change(self):
        a = _write_tmp(MODEL_A)
        b = _write_tmp(MODEL_B)
        try:
            diffs = compute_diff(a, b)
            constraint_diffs = [d for d in diffs if d[1] == "Constraint"]
            assert len(constraint_diffs) >= 0
        finally:
            os.unlink(a)
            os.unlink(b)

    def test_overall_diff_count(self):
        a = _write_tmp(MODEL_A)
        b = _write_tmp(MODEL_B)
        try:
            diffs = compute_diff(a, b)
            assert len(diffs) >= 5
        finally:
            os.unlink(a)
            os.unlink(b)
