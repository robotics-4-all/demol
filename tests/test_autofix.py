"""Tests for the auto-fix engine."""

import pytest
from demol.cli.autofix import (
    apply_fixes,
    fix_missing_network,
    fix_missing_broker,
    fix_missing_broker_auth,
    fix_sampling_on_change_threshold,
    fix_sampling_batch_buffer,
)

MINIMAL_NO_NETWORK_NO_BROKER = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];
"""

MINIMAL_WITH_NETWORK = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
NETWORK[WiFi] WITH ssid="test", password="pass123";
"""

MINIMAL_WITH_BROKER = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
BROKER[MQTT] Local WITH host="localhost", port=1883;
"""

REMOTE_BROKER_NO_AUTH = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
BROKER[MQTT] Cloud WITH host="mqtt.example.com", port=1883;
"""

REMOTE_BROKER_WITH_AUTH = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
BROKER[MQTT] Cloud WITH host="mqtt.example.com", port=1883,
    auth.username="user", auth.password="pass";
"""

LOCAL_BROKER = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
BROKER[MQTT] Local WITH host="localhost", port=1883;
"""

SAMPLING_ON_CHANGE_NO_THRESHOLD = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];
SAMPLING EnvSensor WITH rate = 10 hz, mode = on_change;
"""

SAMPLING_ON_CHANGE_WITH_THRESHOLD = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];
SAMPLING EnvSensor WITH rate = 10 hz, mode = on_change, threshold = 0.5;
"""

SAMPLING_BATCH_NO_BUFFER = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];
SAMPLING EnvSensor WITH rate = 10 hz, mode = batch;
"""

SAMPLING_BATCH_WITH_BUFFER = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];
SAMPLING EnvSensor WITH rate = 10 hz, mode = batch, buffer = 20;
"""


class TestFixMissingNetwork:
    def test_adds_network_when_missing(self):
        fixed, descs = apply_fixes(MINIMAL_NO_NETWORK_NO_BROKER)
        assert "NETWORK[WiFi]" in fixed
        assert any("NETWORK" in d for d in descs)

    def test_skips_when_present(self):
        lines = MINIMAL_WITH_NETWORK.splitlines(keepends=True)
        result = fix_missing_network(lines)
        assert result is None


class TestFixMissingBroker:
    def test_adds_broker_when_missing(self):
        fixed, descs = apply_fixes(MINIMAL_NO_NETWORK_NO_BROKER)
        assert "BROKER[MQTT]" in fixed
        assert any("BROKER" in d for d in descs)

    def test_skips_when_present(self):
        lines = MINIMAL_WITH_BROKER.splitlines(keepends=True)
        result = fix_missing_broker(lines)
        assert result is None


class TestFixMissingBrokerAuth:
    def test_adds_auth_to_remote_broker(self):
        fixed, descs = apply_fixes(REMOTE_BROKER_NO_AUTH)
        assert "auth.username" in fixed
        assert "auth.password" in fixed
        assert any("auth" in d.lower() for d in descs)

    def test_skips_local_broker(self):
        lines = LOCAL_BROKER.splitlines(keepends=True)
        result = fix_missing_broker_auth(lines)
        assert result is None

    def test_skips_broker_with_auth(self):
        lines = REMOTE_BROKER_WITH_AUTH.splitlines(keepends=True)
        result = fix_missing_broker_auth(lines)
        assert result is None


class TestFixSamplingOnChangeThreshold:
    def test_adds_threshold_when_missing(self):
        fixed, descs = apply_fixes(SAMPLING_ON_CHANGE_NO_THRESHOLD)
        assert "threshold" in fixed
        assert any("threshold" in d for d in descs)

    def test_skips_when_present(self):
        lines = SAMPLING_ON_CHANGE_WITH_THRESHOLD.splitlines(keepends=True)
        result = fix_sampling_on_change_threshold(lines)
        assert result is None


class TestFixSamplingBatchBuffer:
    def test_adds_buffer_when_missing(self):
        fixed, descs = apply_fixes(SAMPLING_BATCH_NO_BUFFER)
        assert "buffer" in fixed
        assert any("buffer" in d for d in descs)

    def test_skips_when_present(self):
        lines = SAMPLING_BATCH_WITH_BUFFER.splitlines(keepends=True)
        result = fix_sampling_batch_buffer(lines)
        assert result is None


class TestApplyFixes:
    def test_no_fixes_needed(self):
        model = """\
DEVICE Test WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
NETWORK[WiFi] WITH ssid="test", password="pass";
BROKER[MQTT] Local WITH host="localhost", port=1883;
"""
        fixed, descs = apply_fixes(model)
        assert len(descs) == 0

    def test_multiple_fixes_combined(self):
        fixed, descs = apply_fixes(MINIMAL_NO_NETWORK_NO_BROKER)
        assert len(descs) >= 2
        assert "NETWORK" in fixed
        assert "BROKER" in fixed

    def test_fix_preserves_existing_content(self):
        fixed, _ = apply_fixes(MINIMAL_NO_NETWORK_NO_BROKER)
        assert "DEVICE Test" in fixed
        assert "USE RaspberryPi_5_8GB" in fixed
        assert "USE BME680[EnvSensor]" in fixed
