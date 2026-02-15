"""Tests for protocol frequency / bus speed validation."""

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


BASE = """
DEVICE TestFreq WITH description="Test", author="Test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[EnvSensor];

NETWORK[WiFi] WITH ssid="test", password="test123";
BROKER[MQTT] Local WITH host="localhost", port=1883;
"""


def _model_with_i2c_speed(speed):
    return BASE + f"""
CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76, bus_speed={speed}] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";
"""


def _model_no_bus_speed():
    return BASE + """
CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";
"""


def test_i2c_standard_mode_no_warning(device_mm):
    """100 kHz standard mode should pass without warnings."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(_model_with_i2c_speed(100000))
    i2c_warnings = [x for x in w if "I2C" in str(x.message) and "HighSpeed" in str(x.message)]
    assert len(i2c_warnings) == 0


def test_i2c_fast_mode_no_warning(device_mm):
    """400 kHz fast mode should pass without warnings."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(_model_with_i2c_speed(400000))
    i2c_warnings = [x for x in w if "I2C" in str(x.message) and "HighSpeed" in str(x.message)]
    assert len(i2c_warnings) == 0


def test_i2c_fast_mode_plus_warning(device_mm):
    """1 MHz fast mode plus should emit a warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(_model_with_i2c_speed(1000000))
    i2c_warnings = [x for x in w if "I2C" in str(x.message) and "HighSpeed" in str(x.message)]
    assert len(i2c_warnings) == 1
    assert "Fast Mode Plus" in str(i2c_warnings[0].message)


def test_i2c_high_speed_warning(device_mm):
    """3.4 MHz high speed mode should emit a warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(_model_with_i2c_speed(3400000))
    i2c_warnings = [x for x in w if "I2C" in str(x.message) and "HighSpeed" in str(x.message)]
    assert len(i2c_warnings) == 1
    assert "High Speed Mode" in str(i2c_warnings[0].message)


def test_i2c_beyond_high_speed_error(device_mm):
    """Above 3.4 MHz should be an error."""
    with pytest.raises(TextXSemanticError, match="exceeds the maximum"):
        device_mm.model_from_str(_model_with_i2c_speed(5000000))


def test_i2c_no_bus_speed_no_issue(device_mm):
    """No bus_speed property should not trigger any frequency validation."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(_model_no_bus_speed())
    i2c_warnings = [x for x in w if "BusSpeed" in str(x.message) or "HighSpeed" in str(x.message)]
    assert len(i2c_warnings) == 0


def test_i2c_low_speed_valid(device_mm):
    """10 kHz (below standard) should pass without issues."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(_model_with_i2c_speed(10000))
    i2c_warnings = [x for x in w if "I2C" in str(x.message) and "HighSpeed" in str(x.message)]
    assert len(i2c_warnings) == 0
