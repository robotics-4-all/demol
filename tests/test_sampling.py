import pytest
import warnings
from textx import TextXSemanticError
from demol.lang.device import get_device_mm


@pytest.fixture
def device_mm():
    return get_device_mm()


BASE_MODEL = """
DEVICE TestDevice WITH description="test", author="test", os=raspbian;
NETWORK[WiFi] WITH ssid="test", password="test";
BROKER[MQTT] test WITH host="localhost", port=1883;

USE RaspberryPi_5_8GB;
USE BME680[Sensor1];
USE HCSR04[Dist];

CONNECT Sensor1 WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";

CONNECT Dist WITH
    POWER GND -- GND_2, VCC -- power_5v_b
    DATA gpio echo -- GPIO17, gpio trigger -- GPIO27
    @ "sensors/distance";
"""


def test_sampling_basic_parse(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Sensor1 WITH rate = 10 hz;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.samplings) == 1
    assert model.samplings[0].target.name == "Sensor1"
    assert model.samplings[0].rate == 10
    assert model.samplings[0].rate_unit == "hz"


def test_sampling_with_mode(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Sensor1 WITH rate = 1 hz, mode = continuous;
    """
    model = device_mm.model_from_str(model_str)
    assert model.samplings[0].mode == "continuous"


def test_sampling_on_change_with_threshold(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Dist WITH rate = 5 hz, mode = on_change, threshold = 0.5;
    """
    model = device_mm.model_from_str(model_str)
    assert model.samplings[0].mode == "on_change"
    assert model.samplings[0].threshold == 0.5


def test_sampling_batch_with_buffer(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Sensor1 WITH rate = 2 hz, mode = batch, buffer = 20;
    """
    model = device_mm.model_from_str(model_str)
    assert model.samplings[0].mode == "batch"
    assert model.samplings[0].buffer == 20


def test_sampling_on_demand(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Sensor1 WITH rate = 1 hz, mode = on_demand;
    """
    model = device_mm.model_from_str(model_str)
    assert model.samplings[0].mode == "on_demand"


def test_sampling_multiple_peripherals(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Sensor1 WITH rate = 1 hz, mode = continuous;
    SAMPLING Dist WITH rate = 10 hz, mode = on_change, threshold = 0.1;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.samplings) == 2


def test_sampling_khz_rate(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Sensor1 WITH rate = 1 khz;
    """
    model = device_mm.model_from_str(model_str)
    assert model.samplings[0].rate_unit == "khz"


def test_sampling_no_samplings_is_fine(device_mm):
    model = device_mm.model_from_str(BASE_MODEL)
    assert len(model.samplings) == 0


def test_sampling_duplicate_target_fails(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Sensor1 WITH rate = 1 hz;
    SAMPLING Sensor1 WITH rate = 5 hz;
    """
    with pytest.raises(TextXSemanticError, match="Duplicate SAMPLING"):
        device_mm.model_from_str(model_str)


def test_sampling_on_change_without_threshold_fails(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Dist WITH rate = 5 hz, mode = on_change;
    """
    with pytest.raises(TextXSemanticError, match="threshold > 0"):
        device_mm.model_from_str(model_str)


def test_sampling_batch_without_buffer_fails(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Sensor1 WITH rate = 2 hz, mode = batch;
    """
    with pytest.raises(TextXSemanticError, match="buffer > 0"):
        device_mm.model_from_str(model_str)


def test_sampling_with_constraint_together(device_mm):
    model_str = BASE_MODEL + """
    SAMPLING Sensor1 WITH rate = 1 hz;
    CONSTRAINT min_sensors: count(SENSOR) >= 2;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.samplings) == 1
    assert len(model.constraints) == 1
