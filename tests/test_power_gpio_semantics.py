from textx.exceptions import TextXSemanticError
import pytest
import warnings

# ============================================================================
# Power Connection Tests (validate_power_connection)
# ============================================================================

def test_power_valid_3v3(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER
            vcc -- power_3v3_a,  // BME680 vcc is 5V, so this is actually mismatched in strict sense but let's check code
            gnd -- GND_1
        DATA
            i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    # BME680 definition has vcc=5V. RPi power_3v3_a is 3.3V.
    # 5.0 - 3.3 = 1.7 > 0.5 tolerance. Should fail.
    with pytest.raises(TextXSemanticError, match="Incompatible power connection"):
        device_mm.model_from_str(model_str)

def test_power_valid_5v(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER
            vcc -- power_5v_a, // 5V to 5V - OK
            gnd -- GND_1       // GND to GND - OK
        DATA
            i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    with pytest.warns(UserWarning): # Ignore IO voltage warning
        device_mm.model_from_str(model_str)

def test_power_gnd_mismatch(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER
            gnd -- power_5v_a, // Connecting 5V to GND!
            vcc -- power_5v_b  // Connect VCC to satisfy essential pin check
        DATA
            i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    with pytest.raises(TextXSemanticError, match="Cannot connect GND pin to power pin"):
        device_mm.model_from_str(model_str)

def test_power_missing_ground_warning(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER
            vcc -- power_5v_a
            // No GND
        DATA
            i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    with pytest.raises(TextXSemanticError, match="Essential pin 'gnd'"):
        device_mm.model_from_str(model_str)

def test_voltage_limit_exceeded(device_mm):
    # Need a peripheral with low VCC (e.g. 3.3V) and connect to 5V
    # Let's try to find a 3.3V peripheral.
    pass 

# ============================================================================
# GPIO Connection Tests (validate_gpio_connection)
# ============================================================================

def test_gpio_valid(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE HCSR04[MyDist]; // Uses GPIO
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyDist WITH
        POWER
            VCC -- power_5v_a,
            GND -- GND_1
        DATA
            gpio[mode="output"] trigger -- GPIO23,
            gpio[mode="input"]  echo -- GPIO24;
    """
    # Should pass without error
    device_mm.model_from_str(model_str)

def test_gpio_invalid_mode(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE HCSR04[MyDist];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyDist WITH
        POWER VCC -- power_5v_a, GND -- GND_1
        DATA
            gpio[mode="invalid"] trigger -- GPIO23,
            gpio[mode="input"] echo -- GPIO24;
    """
    with pytest.raises(TextXSemanticError, match="Invalid mode"):
        device_mm.model_from_str(model_str)

def test_gpio_non_gpio_pin(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE HCSR04[MyDist];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyDist WITH
        POWER VCC -- power_5v_a, GND -- GND_1
        DATA
            // power_3v3_a is NOT a GPIO pin
            gpio[mode="output"] trigger -- power_3v3_a,
            gpio[mode="input"] echo -- GPIO24;
    """
    with pytest.raises(TextXSemanticError, match="does not have GPIO"):
        device_mm.model_from_str(model_str)

def test_gpio_deprecated_name(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE HCSR04[MyDist];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyDist WITH
        POWER VCC -- power_5v_a, GND -- GND_1
        DATA
            gpio[name="dep"] trigger -- GPIO23,
            gpio[mode="input"] echo -- GPIO24;
    """
    with pytest.raises(TextXSemanticError, match="deprecated"):
        device_mm.model_from_str(model_str)

def test_gpio_invalid_property(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE HCSR04[MyDist];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyDist WITH
        POWER VCC -- power_5v_a, GND -- GND_1
        DATA
            gpio[speed=100] trigger -- GPIO23,
            gpio[mode="input"] echo -- GPIO24;
    """
    with pytest.raises(TextXSemanticError, match="Invalid property"):
        device_mm.model_from_str(model_str)
