"""Tests for the DeMoL Language Server."""

import pytest
from demol.lsp.server import (
    create_server,
    _parse_and_validate,
    _extract_instance_names,
    _extract_broker_names,
    _get_word_at_position,
    _get_component_library,
    _scan_hwd_files,
)
from demol.definitions import BOARD_MODEL_REPO_PATH, PERIPHERAL_MODEL_REPO_PATH

VALID_MODEL = """
DEVICE TestLSP WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];
USE BuzzerGeneric[Alarm];

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
"""

INVALID_MODEL = """
DEVICE TestBad WITH description="Test", author="Test";
USE RaspberryPi_5_8GB;
"""


class TestParseAndValidate:
    def test_valid_model_no_errors(self):
        model, errors, warns = _parse_and_validate(VALID_MODEL)
        assert model is not None
        assert len(errors) == 0

    def test_invalid_model_has_errors(self):
        model, errors, warns = _parse_and_validate(INVALID_MODEL)
        assert len(errors) > 0

    def test_syntax_error_captured(self):
        _, errors, _ = _parse_and_validate("INVALID SYNTAX HERE !!!")
        assert len(errors) > 0
        assert any("message" in e for e in errors)


class TestExtractors:
    def test_extract_instance_names_bracket(self):
        names = _extract_instance_names(VALID_MODEL)
        assert "EnvSensor" in names
        assert "Alarm" in names

    def test_extract_instance_names_empty(self):
        names = _extract_instance_names('DEVICE Foo WITH description="x";')
        assert len(names) == 0

    def test_extract_broker_names(self):
        names = _extract_broker_names(VALID_MODEL)
        assert "Cloud" in names
        assert "Local" in names

    def test_extract_broker_names_empty(self):
        names = _extract_broker_names('DEVICE Foo WITH description="x";')
        assert len(names) == 0


class TestWordAtPosition:
    def test_word_in_middle(self):
        word, start, end = _get_word_at_position("USE BME680[EnvSensor];", 4)
        assert word == "BME680"

    def test_word_at_start(self):
        word, start, end = _get_word_at_position("DEVICE TestLSP", 0)
        assert word == "DEVICE"

    def test_word_boundary(self):
        word, start, end = _get_word_at_position("USE BME680", 4)
        assert word == "BME680"

    def test_past_end(self):
        word, start, end = _get_word_at_position("abc", 100)
        assert word is None


class TestComponentLibrary:
    def test_scan_boards(self):
        boards = _scan_hwd_files(BOARD_MODEL_REPO_PATH)
        assert len(boards) > 0
        assert "RaspberryPi_5_8GB" in boards

    def test_scan_peripherals(self):
        peripherals = _scan_hwd_files(PERIPHERAL_MODEL_REPO_PATH)
        assert len(peripherals) > 0
        assert "BME680" in peripherals

    def test_full_library(self):
        lib = _get_component_library()
        assert "RaspberryPi_5_8GB" in lib
        assert "BME680" in lib
        for name, info in lib.items():
            assert "path" in info
            assert "content" in info
            assert "filename" in info

    def test_scan_nonexistent_dir(self):
        result = _scan_hwd_files("/nonexistent/path")
        assert result == {}


class TestServerCreation:
    def test_create_server(self):
        server = create_server()
        assert server is not None
        assert server.name == "demol-lsp"
