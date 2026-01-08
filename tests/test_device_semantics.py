from textx.exceptions import TextXSemanticError
import pytest
import warnings

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
            power_5v_a -- VCC,
            GND_1 -- GND
        DATA
            gpio[mode="output"] GPIO23 -- trigger,
            gpio[mode="input"] GPIO24 -- echo
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
            power_5v_a -- vcc
            // Missing GND
        DATA
            i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl
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
            power_5v_a -- vcc,
            GND_1 -- gnd
        DATA
            i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl
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
            power_5v_a -- vcc,
            GND_1 -- gnd
        DATA
            // GPIO4 does not have SDA function
            i2c[slave_address=0x76] sda GPIO4 -- sda, scl GPIO3 -- scl
        @ "test/topic";
    """
    with pytest.raises(TextXSemanticError, match="does not have SDA"):
        device_mm.model_from_str(model_str)
