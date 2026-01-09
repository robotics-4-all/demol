from textx.exceptions import TextXSemanticError
import pytest
import warnings

# ============================================================================
# UART Connection Tests (validate_uart_connection)
# ============================================================================

# We need a UART peripheral. tfmini is usually UART.
# Let's check tfmini.hwd content first to be sure.
# Assuming tfmini has tx/rx pins.

def test_uart_valid(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE TFMini[MyLidar];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLidar WITH
        POWER VCC -- power_5v_a, GND -- GND_1
        DATA
            // RPi TX (GPIO14) -> TFMini RXD
            // RPi RX (GPIO15) <- TFMini TXD
            uart[baudrate=115200] tx RXD -- GPIO14, rx TXD -- GPIO15;
    """
    # Should pass without error
    device_mm.model_from_str(model_str)

def test_uart_invalid_baudrate_negative(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE TFMini[MyLidar];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLidar WITH
        POWER VCC -- power_5v_a, GND -- GND_1
        DATA
            uart[baudrate=-1] tx RXD -- GPIO14, rx TXD -- GPIO15;
    """
    with pytest.raises(TextXSemanticError, match="must be positive"):
        device_mm.model_from_str(model_str)

def test_uart_unusual_baudrate(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE TFMini[MyLidar];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLidar WITH
        POWER VCC -- power_5v_a, GND -- GND_1
        DATA
            uart[baudrate=12345] tx RXD -- GPIO14, rx TXD -- GPIO15;
    """
    with pytest.raises(TextXSemanticError, match="Unusual UART baudrate"):
        device_mm.model_from_str(model_str)

def test_uart_missing_function(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE TFMini[MyLidar];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLidar WITH
        POWER VCC -- power_5v_a, GND -- GND_1
        DATA
            // GPIO23 is not TX
            uart[baudrate=115200] tx RXD -- GPIO23, rx TXD -- GPIO15;
    """
    with pytest.raises(TextXSemanticError, match="does not have TX"):
        device_mm.model_from_str(model_str)

def test_uart_wrong_connection_direction(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE TFMini[MyLidar];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLidar WITH
        POWER VCC -- power_5v_a, GND -- GND_1
        DATA
            // Connecting Board TX to Peripheral TXD (invalid)
            uart[baudrate=115200] tx TXD -- GPIO14, rx RXD -- GPIO15;
    """
    with pytest.raises(TextXSemanticError, match="does not have RX"):
        device_mm.model_from_str(model_str)

# ============================================================================
# Safety Tests (validate_no_pin_conflicts, etc.)
# ============================================================================

def test_pin_conflict_gpio(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE HCSR04[Dist1];
    USE HCSR04[Dist2];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT Dist1 WITH
        POWER VCC -- power_5v_a, GND -- GND_1
        DATA gpio[mode="output"] trigger -- GPIO23, gpio[mode="input"] echo -- GPIO24;
        
    CONNECT Dist2 WITH
        POWER VCC -- power_5v_b, GND -- GND_2
        DATA gpio[mode="output"] trigger -- GPIO23, // Conflict on GPIO23
             gpio[mode="input"] echo -- GPIO25;
    """
    with pytest.raises(TextXSemanticError, match="Pin conflict"):
        device_mm.model_from_str(model_str)

def test_pin_sharing_i2c_allowed(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[Sensor1];
    USE BME680[Sensor2];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT Sensor1 WITH
        POWER vcc -- power_5v_a, gnd -- GND_1
        DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
        
    CONNECT Sensor2 WITH
        POWER vcc -- power_5v_b, gnd -- GND_2
        DATA i2c[slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3; // Shared I2C pins OK
    """
    with pytest.warns(UserWarning):
        device_mm.model_from_str(model_str)

def test_i2c_address_conflict(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[Sensor1];
    USE BME680[Sensor2];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT Sensor1 WITH
        POWER vcc -- power_5v_a, gnd -- GND_1
        DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
        
    CONNECT Sensor2 WITH
        POWER vcc -- power_5v_b, gnd -- GND_2
        DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3; // Same address!
    """
    with pytest.raises(TextXSemanticError, match="I2C address conflict"):
        device_mm.model_from_str(model_str)

def test_unique_peripheral_names(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    USE HCSR04[MySensor]; // Duplicate name
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER vcc -- power_5v_a, gnd -- GND_1
        DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    # TextX might catch this as a duplicate definition first
    from textx.exceptions import TextXError
    with pytest.raises(TextXError):
        device_mm.model_from_str(model_str)

def test_unconnected_peripheral(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    USE BME680[UnconnectedSensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MySensor WITH
        POWER vcc -- power_5v_a, gnd -- GND_1
        DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    with pytest.raises(TextXSemanticError, match="Unconnected peripherals detected"):
        device_mm.model_from_str(model_str)

def test_missing_broker(device_mm):
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE BME680[MySensor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    // No BROKER
    
    CONNECT MySensor WITH
        POWER vcc -- power_5v_a, gnd -- GND_1
        DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    with pytest.raises(TextXSemanticError, match="Broker configuration required"):
        device_mm.model_from_str(model_str)
