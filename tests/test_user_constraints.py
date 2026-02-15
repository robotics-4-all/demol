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

CONNECT Sensor1 WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";
"""

SERVO_MODEL = """
DEVICE TestDevice WITH description="test", author="test", os=raspbian;
NETWORK[WiFi] WITH ssid="test", password="test";
BROKER[MQTT] test WITH host="localhost", port=1883;

USE RaspberryPi_5_8GB;
USE ServoGeneric[PanServo] WITH min_angle = -90.0, max_angle = 90.0;

CONNECT PanServo WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA gpio[mode="output"] din -- GPIO12
    @ "servos/pan";
"""

MULTI_PERIPHERAL_MODEL = """
DEVICE TestDevice WITH description="test", author="test", os=raspbian;
NETWORK[WiFi] WITH ssid="test", password="test";
BROKER[MQTT] test WITH host="localhost", port=1883;

USE RaspberryPi_5_8GB;
USE BME680[Sensor1];
USE HCSR04[DistSensor];
USE LedGeneric[StatusLed];

CONNECT Sensor1 WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";

CONNECT DistSensor WITH
    POWER GND -- GND_2, VCC -- power_5v_b
    DATA gpio echo -- GPIO17, gpio trigger -- GPIO27
    @ "sensors/distance";

CONNECT StatusLed WITH
    POWER gnd -- GND_3, vcc -- power_3v3_a
    DATA gpio[mode="output"] vin -- GPIO22
    @ "actuators/led";
"""


def test_count_sensor_passing(device_mm):
    model_str = BASE_MODEL + """
    CONSTRAINT min_sensors: count(SENSOR) >= 1;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1
    assert model.constraints[0].name == "min_sensors"


def test_count_sensor_failing(device_mm):
    model_str = BASE_MODEL + """
    CONSTRAINT need_many: count(SENSOR) >= 5
        MESSAGE "Need at least 5 sensors";
    """
    with pytest.raises(TextXSemanticError, match="Constraint-Violated"):
        device_mm.model_from_str(model_str)


def test_count_actuator(device_mm):
    model_str = MULTI_PERIPHERAL_MODEL + """
    CONSTRAINT has_actuator: count(ACTUATOR) >= 1;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_count_peripheral_total(device_mm):
    model_str = MULTI_PERIPHERAL_MODEL + """
    CONSTRAINT enough: count(PERIPHERAL) >= 3;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_count_connection(device_mm):
    model_str = MULTI_PERIPHERAL_MODEL + """
    CONSTRAINT conn_count: count(CONNECTION) >= 3;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_property_access_passing(device_mm):
    model_str = SERVO_MODEL + """
    CONSTRAINT angle_ok: PanServo.max_angle <= 180.0;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_property_access_failing(device_mm):
    model_str = SERVO_MODEL + """
    CONSTRAINT angle_strict: PanServo.max_angle <= 45.0
        MESSAGE "Max angle must be <= 45 degrees";
    """
    with pytest.raises(TextXSemanticError, match="Constraint-Violated"):
        device_mm.model_from_str(model_str)


def test_property_access_negative_value(device_mm):
    model_str = SERVO_MODEL + """
    CONSTRAINT min_ok: PanServo.min_angle >= -90.0;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_sum_power_passing(device_mm):
    model_str = BASE_MODEL + """
    CONSTRAINT power_ok: sum_power(PERIPHERAL) < 5000 mW;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_sum_power_failing(device_mm):
    model_str = BASE_MODEL + """
    CONSTRAINT power_tight: sum_power(PERIPHERAL) < 1 mW
        MESSAGE "Power budget too tight";
    """
    with pytest.raises(TextXSemanticError, match="Constraint-Violated"):
        device_mm.model_from_str(model_str)


def test_arithmetic_addition(device_mm):
    model_str = MULTI_PERIPHERAL_MODEL + """
    CONSTRAINT total: count(SENSOR) + count(ACTUATOR) >= 3;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_arithmetic_subtraction(device_mm):
    model_str = MULTI_PERIPHERAL_MODEL + """
    CONSTRAINT diff: count(SENSOR) - count(ACTUATOR) >= 1;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_arithmetic_multiplication(device_mm):
    model_str = SERVO_MODEL + """
    CONSTRAINT doubled: PanServo.max_angle * 2 <= 200.0;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_arithmetic_division(device_mm):
    model_str = SERVO_MODEL + """
    CONSTRAINT halved: PanServo.max_angle / 2 <= 50.0;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_custom_message_in_error(device_mm):
    model_str = BASE_MODEL + """
    CONSTRAINT fail_msg: count(SENSOR) >= 10
        MESSAGE "Custom error: need 10 sensors for redundancy";
    """
    with pytest.raises(
        TextXSemanticError,
        match="Custom error: need 10 sensors for redundancy",
    ):
        device_mm.model_from_str(model_str)


def test_no_message_generates_default(device_mm):
    model_str = BASE_MODEL + """
    CONSTRAINT fail_no_msg: count(SENSOR) >= 10;
    """
    with pytest.raises(TextXSemanticError, match="failed"):
        device_mm.model_from_str(model_str)


def test_unknown_peripheral_warns(device_mm):
    model_str = BASE_MODEL + """
    CONSTRAINT bad_ref: NonExistent.some_attr >= 1;
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        eval_errors = [x for x in w if "ConstraintEvalError" in str(x.message)]
        assert len(eval_errors) == 1
        assert "Unknown peripheral" in str(eval_errors[0].message)


def test_unknown_attribute_warns(device_mm):
    model_str = BASE_MODEL + """
    CONSTRAINT bad_attr: Sensor1.nonexistent_attr >= 1;
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        eval_errors = [x for x in w if "ConstraintEvalError" in str(x.message)]
        assert len(eval_errors) == 1
        assert "has no attribute" in str(eval_errors[0].message)


def test_multiple_constraints_all_pass(device_mm):
    model_str = MULTI_PERIPHERAL_MODEL + """
    CONSTRAINT c1: count(SENSOR) >= 2;
    CONSTRAINT c2: count(ACTUATOR) >= 1;
    CONSTRAINT c3: count(PERIPHERAL) >= 3;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 3


def test_multiple_constraints_one_fails(device_mm):
    model_str = MULTI_PERIPHERAL_MODEL + """
    CONSTRAINT c1: count(SENSOR) >= 2;
    CONSTRAINT c2: count(ACTUATOR) >= 10
        MESSAGE "Not enough actuators";
    """
    with pytest.raises(TextXSemanticError, match="Not enough actuators"):
        device_mm.model_from_str(model_str)


def test_no_constraints_no_error(device_mm):
    model = device_mm.model_from_str(BASE_MODEL)
    assert len(model.constraints) == 0


def test_comparison_operators(device_mm):
    for op, val, should_pass in [
        ("<", 2, True),
        (">", 0, True),
        ("<=", 1, True),
        (">=", 1, True),
        ("==", 1, True),
        ("!=", 0, True),
        ("<", 0, False),
        (">", 1, False),
        ("==", 0, False),
        ("!=", 1, False),
    ]:
        model_str = BASE_MODEL + f"""
        CONSTRAINT cmp: count(SENSOR) {op} {val};
        """
        if should_pass:
            device_mm.model_from_str(model_str)
        else:
            with pytest.raises(TextXSemanticError, match="Constraint-Violated"):
                device_mm.model_from_str(model_str)


def test_power_unit_normalization(device_mm):
    model_str = BASE_MODEL + """
    CONSTRAINT power_w: sum_power(PERIPHERAL) < 5 W;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_max_power_function(device_mm):
    model_str = MULTI_PERIPHERAL_MODEL + """
    CONSTRAINT max_ok: max_power(PERIPHERAL) < 10000 mW;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_avg_power_function(device_mm):
    model_str = MULTI_PERIPHERAL_MODEL + """
    CONSTRAINT avg_ok: avg_power(PERIPHERAL) < 10000 mW;
    """
    model = device_mm.model_from_str(model_str)
    assert len(model.constraints) == 1


def test_skip_semantics_bypasses_constraint_errors(device_mm):
    mm = get_device_mm(skip_semantics=True)
    model_str = BASE_MODEL + """
    CONSTRAINT will_fail: count(SENSOR) >= 100;
    """
    model = mm.model_from_str(model_str)
    assert len(model.constraints) == 1
