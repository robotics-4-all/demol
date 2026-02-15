import pytest
import warnings
from demol.lang.device import get_device_mm


@pytest.fixture
def device_mm():
    return get_device_mm()


def test_gpio_on_i2c_pin_warns(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=raspbian;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE RaspberryPi_5_8GB;
    USE TactileButton[Btn];

    CONNECT Btn WITH
        POWER gnd -- GND_1
        DATA gpio[mode="input"] state -- GPIO2
        @ "sensors/button";
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        oversub_warnings = [x for x in w if "PinOversubscriptionWarning" in str(x.message)]
        assert len(oversub_warnings) >= 1
        msg = str(oversub_warnings[0].message)
        assert "GPIO2" in msg
        assert "I2C" in msg
        assert "Warning-Pin-Oversubscription" in msg


def test_gpio_on_plain_gpio_pin_no_warning(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=raspbian;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE RaspberryPi_5_8GB;
    USE TactileButton[Btn];

    CONNECT Btn WITH
        POWER gnd -- GND_1
        DATA gpio[mode="input"] state -- GPIO4
        @ "sensors/button";
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        oversub_warnings = [x for x in w if "PinOversubscriptionWarning" in str(x.message)]
        assert len(oversub_warnings) == 0


def test_i2c_on_i2c_pin_no_warning(device_mm):
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
        oversub_warnings = [x for x in w if "PinOversubscriptionWarning" in str(x.message)]
        assert len(oversub_warnings) == 0


def test_gpio_on_spi_pin_warns(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=raspbian;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE RaspberryPi_5_8GB;
    USE LedGeneric[Led1];

    CONNECT Led1 WITH
        POWER gnd -- GND_1, vcc -- power_3v3_a
        DATA gpio[mode="output"] vin -- GPIO10
        @ "actuators/led";
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        oversub_warnings = [x for x in w if "PinOversubscriptionWarning" in str(x.message)]
        assert len(oversub_warnings) >= 1
        msg = str(oversub_warnings[0].message)
        assert "GPIO10" in msg
        assert "SPI" in msg


def test_gpio_on_uart_pin_warns(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=raspbian;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE RaspberryPi_5_8GB;
    USE LedGeneric[Led1];

    CONNECT Led1 WITH
        POWER gnd -- GND_1, vcc -- power_3v3_a
        DATA gpio[mode="output"] vin -- GPIO14
        @ "actuators/led";
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        oversub_warnings = [x for x in w if "PinOversubscriptionWarning" in str(x.message)]
        assert len(oversub_warnings) >= 1
        msg = str(oversub_warnings[0].message)
        assert "GPIO14" in msg
        assert "UART" in msg


def test_gpio_on_pwm_pin_warns(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=raspbian;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE RaspberryPi_5_8GB;
    USE LedGeneric[Led1];

    CONNECT Led1 WITH
        POWER gnd -- GND_1, vcc -- power_3v3_a
        DATA gpio[mode="output"] vin -- GPIO18
        @ "actuators/led";
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        oversub_warnings = [x for x in w if "PinOversubscriptionWarning" in str(x.message)]
        assert len(oversub_warnings) >= 1
        msg = str(oversub_warnings[0].message)
        assert "GPIO18" in msg


def test_warning_message_suggests_alternative(device_mm):
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=raspbian;
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] test WITH host="localhost", port=1883;

    USE RaspberryPi_5_8GB;
    USE TactileButton[Btn];

    CONNECT Btn WITH
        POWER gnd -- GND_1
        DATA gpio[mode="input"] state -- GPIO2
        @ "sensors/button";
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        oversub_warnings = [x for x in w if "PinOversubscriptionWarning" in str(x.message)]
        assert len(oversub_warnings) >= 1
        assert "Use a different pin" in str(oversub_warnings[0].message)
