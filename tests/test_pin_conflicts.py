import pytest
from textx import TextXSemanticError
from demol.lang.device import get_device_mm

def test_gpio_pin_conflict():
    """Test that connecting two peripherals to the same GPIO pin raises a PinConflictError."""
    model_str = """
    DEVICE PinConflictTest WITH description="Test GPIO Conflict", author="Tester", os=raspbian;
    USE RaspberryPi_5_8GB;
    USE LedGeneric[Led1], LedGeneric[Led2];
    
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT Led1 WITH
        POWER gnd -- GND_1, vcc -- power_3v3_a
        DATA gpio[mode="output"] vin -- GPIO18
    @ "led1";
    
    CONNECT Led2 WITH
        POWER gnd -- GND_2, vcc -- power_3v3_b
        DATA gpio[mode="output"] vin -- GPIO18
    @ "led2";
    """
    mm = get_device_mm()
    with pytest.raises(TextXSemanticError, match=r"Pin conflict detected"):
        mm.model_from_str(model_str)

def test_i2c_pin_sharing_allowed():
    """Test that sharing I2C pins (SDA/SCL) is allowed."""
    model_str = """
    DEVICE I2CSharingTest WITH description="Test I2C Sharing", author="Tester", os=raspbian;
    USE RaspberryPi_5_8GB;
    USE BME680[Sensor1], BME680[Sensor2];
    
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT Sensor1 WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensor1";
    
    CONNECT Sensor2 WITH
        POWER gnd -- GND_2, vcc -- power_5v_b
        DATA i2c[slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensor2";
    """
    mm = get_device_mm()
    # Should not raise an error
    mm.model_from_str(model_str)

def test_power_pin_sharing_allowed():
    """Test that sharing Power pins (GND/VCC) is allowed."""
    model_str = """
    DEVICE PowerSharingTest WITH description="Test Power Sharing", author="Tester", os=raspbian;
    USE RaspberryPi_5_8GB;
    USE LedGeneric[Led1], LedGeneric[Led2];
    
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT Led1 WITH
        POWER gnd -- GND_1, vcc -- power_3v3_a
        DATA gpio[mode="output"] vin -- GPIO18
    @ "led1";
    
    CONNECT Led2 WITH
        POWER gnd -- GND_1, vcc -- power_3v3_a
        DATA gpio[mode="output"] vin -- GPIO19
    @ "led2";
    """
    mm = get_device_mm()
    # Should not raise an error
    mm.model_from_str(model_str)

def test_mixed_usage_conflict():
    """Test conflict between GPIO and Special Function (e.g. UART) on same pin."""
    model_str = """
    DEVICE MixedConflictTest WITH description="Test Mixed Conflict", author="Tester", os=raspbian;
    USE RaspberryPi_5_8GB;
    USE LedGeneric[Led1];
    USE TFMini[Lidar];
    
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT Led1 WITH
        POWER gnd -- GND_1, vcc -- power_3v3_a
        DATA gpio[mode="output"] vin -- GPIO14
    @ "led1";
    
    CONNECT Lidar WITH
        POWER GND -- GND_2, VCC -- power_5v_a
        DATA uart[baudrate=115200] tx RXD -- GPIO14, rx TXD -- GPIO15
    @ "lidar";
    """
    mm = get_device_mm()
    with pytest.raises(TextXSemanticError, match=r"Pin conflict detected"):
        mm.model_from_str(model_str)
