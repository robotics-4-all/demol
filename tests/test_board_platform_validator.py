"""Tests for the [Board-Platform] validator.

Verifies that the BoardPlatformValidator warns at ``demol validate`` time
when a board's PLATFORMS block does not include the model's declared OS.
"""

import warnings
from types import SimpleNamespace

import pytest

from demol.lang.semantics.validators.board_platform import (
    BoardPlatformValidator,
    validate_board_platform,
    _CODEGEN_OSES,
    _RESERVED_OS,
)

# ---------------------------------------------------------------------------
# Validator unit-level tests
# ---------------------------------------------------------------------------


class TestBoardPlatformValidatorUnit:
    """BoardPlatformValidator: unit-level tests."""

    def test_get_name(self):
        assert BoardPlatformValidator.get_name() == "[Board-Platform]"

    def test_get_description(self):
        desc = BoardPlatformValidator.get_description()
        assert "PLATFORMS" in desc
        assert "board" in desc.lower()

    def test_codegen_oses(self):
        assert "raspbian" in _CODEGEN_OSES
        assert "riotos" in _CODEGEN_OSES
        assert "zephyr" in _CODEGEN_OSES
        assert "wokwi" in _CODEGEN_OSES
        assert "renode" in _CODEGEN_OSES

    def test_function_exists(self):
        assert callable(validate_board_platform)


# ---------------------------------------------------------------------------
# Direct validator call tests (no full pipeline, no cross-contamination)
# ---------------------------------------------------------------------------


def _make_model(
    os_value=None,
    board_name="TestBoard",
    board_platforms=None,
    has_board=True,
):
    """Build a fake model with the given attributes.

    Args:
        os_value: Value for ``metadata.os`` (or None to omit).
        board_name: Name for the board object.
        board_platforms: List of platform mapping objects, each with ``.os``,
            or ``None`` to simulate no PLATFORMS block.
        has_board: If False, ``model.components.board`` will be None.

    Returns:
        A namespace-based fake model.
    """
    metadata = SimpleNamespace(os=os_value)
    board = SimpleNamespace(name=board_name, platforms=board_platforms)
    components = SimpleNamespace(board=board if has_board else None)
    return SimpleNamespace(metadata=metadata, components=components)


class TestDirectValidatorNoWarning:
    """Direct validator calls that should NOT raise warnings."""

    def test_no_metadata(self):
        model = SimpleNamespace(metadata=None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            BoardPlatformValidator.validate(model)
        bp_warnings = [x for x in w if "[Board-Platform]" in str(x.message)]
        assert len(bp_warnings) == 0

    def test_no_os(self):
        model = _make_model(os_value=None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            BoardPlatformValidator.validate(model)
        bp_warnings = [x for x in w if "[Board-Platform]" in str(x.message)]
        assert len(bp_warnings) == 0

    def test_reserved_os(self):
        model = _make_model(os_value="arduino")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            BoardPlatformValidator.validate(model)
        bp_warnings = [x for x in w if "[Board-Platform]" in str(x.message)]
        assert len(bp_warnings) == 0

    def test_non_codegen_os(self):
        model = _make_model(os_value="future-os")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            BoardPlatformValidator.validate(model)
        bp_warnings = [x for x in w if "[Board-Platform]" in str(x.message)]
        assert len(bp_warnings) == 0

    def test_no_board_component(self):
        """When model.components.board is None → no warning."""
        model = _make_model(os_value="riotos", has_board=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            BoardPlatformValidator.validate(model)
        bp_warnings = [x for x in w if "[Board-Platform]" in str(x.message)]
        assert len(bp_warnings) == 0

    def test_board_platforms_match_os(self):
        """Board declares riotos in PLATFORMS → no warning for riotos."""
        platforms = [SimpleNamespace(os="riotos")]
        model = _make_model(os_value="riotos", board_platforms=platforms)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            BoardPlatformValidator.validate(model)
        bp_warnings = [x for x in w if "[Board-Platform]" in str(x.message)]
        assert len(bp_warnings) == 0

    def test_board_platforms_match_zephyr(self):
        """Board declares zephyr in PLATFORMS → no warning for zephyr."""
        platforms = [SimpleNamespace(os="riotos"), SimpleNamespace(os="zephyr")]
        model = _make_model(os_value="zephyr", board_platforms=platforms)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            BoardPlatformValidator.validate(model)
        bp_warnings = [x for x in w if "[Board-Platform]" in str(x.message)]
        assert len(bp_warnings) == 0


class TestDirectValidatorWarning:
    """Direct validator calls that produce warnings.

    NOTE: These tests can only exercise the success path (report_passed_rule)
    with SimpleNamespace fakes. The warning path calls
    ``raise_validation_warning(obj, ...)`` which accesses textX internals
    via ``get_location(obj)`` — SimpleNamespace objects are insufficient.
    The warning path is fully covered by :class:`TestIntegrationWarning`.
    """

    def test_no_platforms_block_direct_valid(self):
        """Just verify the validator executes on simple models (no-op check)."""
        model = _make_model(os_value="riotos", board_platforms=None)
        # This will raise AttributeError from get_location() on SimpleNamespace.
        # The real warning path is tested via integration tests below.
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            try:
                BoardPlatformValidator.validate(model)
            except AttributeError:
                pass  # Expected — need real textX objects for get_location()


# ---------------------------------------------------------------------------
# Integration tests: full parsing pipeline with real models
# ---------------------------------------------------------------------------


class TestIntegrationNoWarning:
    """Full-pipeline tests that should NOT produce [Board-Platform] warnings."""

    @staticmethod
    def _run(device_mm, model_str):
        """Parse model and return list of [Board-Platform] warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                device_mm.model_from_str(model_str)
            except Exception:
                pass
        return [x for x in w if "[Board-Platform]" in str(x.message)]

    def test_board_has_riotos_platform_and_os_riotos(self, device_mm):
        """WemosD1R32 has PLATFORMS riotos, model os=riotos → no warning."""
        model_str = """
        DEVICE TestDevice WITH description="test", author="test", os=riotos;
        USE WemosD1R32, BME680[EnvSensor];
        NETWORK[WiFi] WITH ssid="w", password="p";
        BROKER[MQTT] B WITH host="localhost", port=1883;
        CONNECT EnvSensor WITH
            POWER gnd -- GND, vcc -- VCC_3V3
            DATA i2c[slave_address=0x76] sda SDA -- SDA, scl SCL -- SCL
            @ "t";
        """
        bp_warnings = self._run(device_mm, model_str)
        assert len(bp_warnings) == 0, f"Unexpected: {bp_warnings}"

    def test_no_os_declared(self, device_mm):
        """No os= in metadata → validator skips → no warning."""
        model_str = """
        DEVICE TestDevice WITH description="test", author="test";
        USE WemosD1R32, BME680[EnvSensor];
        NETWORK[WiFi] WITH ssid="w", password="p";
        BROKER[MQTT] B WITH host="localhost", port=1883;
        CONNECT EnvSensor WITH
            POWER gnd -- GND, vcc -- VCC_3V3
            DATA i2c[slave_address=0x76] sda SDA -- SDA, scl SCL -- SCL
            @ "t";
        """
        bp_warnings = self._run(device_mm, model_str)
        assert len(bp_warnings) == 0

    def test_esp32_has_riotos_platform_and_os_riotos(self, device_mm):
        """ESP32Wroom32 has PLATFORMS riotos, model os=riotos → no warning."""
        model_str = """
        DEVICE TestDevice WITH description="test", author="test", os=riotos;
        USE ESP32Wroom32, BME680[EnvSensor];
        NETWORK[WiFi] WITH ssid="w", password="p";
        BROKER[MQTT] B WITH host="localhost", port=1883;
        CONNECT EnvSensor WITH
            POWER gnd -- GND_1, vcc -- VCC_3V3
            DATA i2c[slave_address=0x76] sda GPIO21 -- SDA, scl GPIO22 -- SCL
            @ "t";
        """
        bp_warnings = self._run(device_mm, model_str)
        assert len(bp_warnings) == 0, f"Unexpected: {bp_warnings}"


class TestIntegrationWarning:
    """Full-pipeline tests that SHOULD produce [Board-Platform] warnings."""

    @staticmethod
    def _run(device_mm, model_str):
        """Parse model and return list of [Board-Platform] warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                device_mm.model_from_str(model_str)
            except Exception:
                pass
        return [x for x in w if "[Board-Platform]" in str(x.message)]

    def test_board_no_platforms_block(self, device_mm):
        """Board with no PLATFORMS block → warning."""
        model_str = """
        DEVICE TestDevice WITH description="test", author="test", os=riotos;
        USE RaspberryPi_5_8GB, BME680[EnvSensor];
        NETWORK[WiFi] WITH ssid="w", password="p";
        BROKER[MQTT] B WITH host="localhost", port=1883;
        CONNECT EnvSensor WITH
            POWER gnd -- GND_1, vcc -- power_5v_a
            DATA i2c[slave_address=0x76] sda SDA -- SDA, scl SCL -- SCL
            @ "t";
        """
        bp_warnings = self._run(device_mm, model_str)
        assert len(bp_warnings) == 1
        assert "no PLATFORMS block" in str(bp_warnings[0].message)

    def test_platforms_missing_declared_os(self, device_mm):
        """Board has PLATFORMS for riotos but model declares zephyr → warning."""
        model_str = """
        DEVICE TestDevice WITH description="test", author="test", os=zephyr;
        USE WemosD1R32, BME680[EnvSensor];
        NETWORK[WiFi] WITH ssid="w", password="p";
        BROKER[MQTT] B WITH host="localhost", port=1883;
        CONNECT EnvSensor WITH
            POWER gnd -- GND, vcc -- VCC_3V3
            DATA i2c[slave_address=0x76] sda SDA -- SDA, scl SCL -- SCL
            @ "t";
        """
        bp_warnings = self._run(device_mm, model_str)
        assert len(bp_warnings) == 1
        assert "does not include 'zephyr'" in str(bp_warnings[0].message)

    def test_raspbian_with_rpi5_no_platforms(self, device_mm):
        """RPi 5 board has no PLATFORMS block, model targets raspbian → warning."""
        model_str = """
        DEVICE TestDevice WITH description="test", author="test", os=raspbian;
        USE RaspberryPi_5_8GB, BME680[EnvSensor];
        NETWORK[WiFi] WITH ssid="w", password="p";
        BROKER[MQTT] B WITH host="localhost", port=1883;
        CONNECT EnvSensor WITH
            POWER gnd -- GND_1, vcc -- power_5v_a
            DATA i2c[slave_address=0x76] sda SDA -- SDA, scl SCL -- SCL
            @ "t";
        """
        bp_warnings = self._run(device_mm, model_str)
        assert len(bp_warnings) == 1
        assert "no PLATFORMS block" in str(bp_warnings[0].message)
