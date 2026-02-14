from textx.exceptions import TextXSemanticError
import pytest


def test_io_voltage_incompatibility(device_mm):
    # RPi4 is 3.3V IO, HCSR04 is 5V IO.
    # This should trigger validate_io_voltage_compatibility which emits a warning

    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE HCSR04[MyDist];
    
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyDist WITH
        POWER
            VCC -- power_5v_a,
            GND -- GND_1
        DATA
            gpio[mode="output"] trigger -- GPIO23,
            gpio[mode="input"] echo -- GPIO24
        @ "test.topic";
    """

    with pytest.warns(UserWarning, match=r".*Safety-IO-Voltage.*"):
        device_mm.model_from_str(model_str)


def test_missing_ground(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER
            vcc -- power_5v_a
            // Missing GND
        DATA
            i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
        @ "test.topic";
    """
    with pytest.raises(TextXSemanticError, match="Essential pin 'gnd'"):
        device_mm.model_from_str(model_str)


def test_invalid_topic(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
        @ "$sys/topic";
    """
    with pytest.raises(TextXSemanticError, match="reserved for system topics"):
        device_mm.model_from_str(model_str)


def test_invalid_pin_function(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            // GPIO4 does not have SDA function
            i2c[slave_address=0x76] sda sda -- GPIO4, scl scl -- GPIO3
        @ "test/topic";
    """
    with pytest.raises(TextXSemanticError, match="does not have SDA"):
        device_mm.model_from_str(model_str)
