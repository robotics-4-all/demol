import pytest
import warnings
from demol.lang.device import get_device_mm


@pytest.fixture
def device_mm():
    return get_device_mm()


def test_power_budget_within_limits(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=raspbian;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE RaspberryPi_5_8GB;
    USE BME680[Sensor1];

    CONNECT Sensor1 WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
        @ "sensors/env";
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        budget_warnings = [x for x in w if "PowerBudgetWarning" in str(x.message)]
        assert len(budget_warnings) == 0


def test_power_budget_exceeded(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=raspbian;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE RaspberryPi_5_8GB;
    USE ServoGeneric[Servo1], ServoGeneric[Servo2], ServoGeneric[Servo3];

    CONNECT Servo1 WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA gpio[mode="output"] din -- GPIO12
        @ "servos/1";
    CONNECT Servo2 WITH
        POWER gnd -- GND_2, vcc -- power_5v_b
        DATA gpio[mode="output"] din -- GPIO13
        @ "servos/2";
    CONNECT Servo3 WITH
        POWER gnd -- GND_3, vcc -- power_5v_a
        DATA gpio[mode="output"] din -- GPIO18
        @ "servos/3";
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        budget_warnings = [x for x in w if "PowerBudgetWarning" in str(x.message)]
        assert len(budget_warnings) == 1
        assert "Safety-Power-Budget" in str(budget_warnings[0].message)
        assert "exceeds board supply" in str(budget_warnings[0].message)


def test_battery_runtime_estimate(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=riotos;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE HCSR04[Sonar];
    USE li_ion_3v7[Battery];

    CONNECT Battery WITH
        POWER vcc -- power_3v3, gnd -- gnd
    ;

    CONNECT Sonar WITH
        POWER GND -- gnd, VCC -- power_5v
        DATA gpio echo -- d0, gpio trigger -- d3
        @ "sensors/distance";
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        runtime_warnings = [x for x in w if "BatteryRuntimeInfo" in str(x.message)]
        assert len(runtime_warnings) == 1
        msg = str(runtime_warnings[0].message)
        assert "Info-Battery-Runtime" in msg
        assert "2500mAh" in msg
        assert "hours" in msg or "minutes" in msg


def test_no_power_budget_warning_without_peripherals(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=raspbian;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE RaspberryPi_5_8GB;
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        budget_warnings = [x for x in w if "PowerBudgetWarning" in str(x.message)]
        assert len(budget_warnings) == 0


def test_power_budget_breakdown_lists_peripherals(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=raspbian;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE RaspberryPi_5_8GB;
    USE ServoGeneric[PanServo], ServoGeneric[TiltServo], ServoGeneric[GripServo];

    CONNECT PanServo WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA gpio[mode="output"] din -- GPIO12
        @ "servos/pan";
    CONNECT TiltServo WITH
        POWER gnd -- GND_2, vcc -- power_5v_b
        DATA gpio[mode="output"] din -- GPIO13
        @ "servos/tilt";
    CONNECT GripServo WITH
        POWER gnd -- GND_3, vcc -- power_5v_a
        DATA gpio[mode="output"] din -- GPIO18
        @ "servos/grip";
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        budget_warnings = [x for x in w if "PowerBudgetWarning" in str(x.message)]
        assert len(budget_warnings) == 1
        msg = str(budget_warnings[0].message)
        assert "PanServo=" in msg
        assert "TiltServo=" in msg
        assert "Breakdown" in msg
