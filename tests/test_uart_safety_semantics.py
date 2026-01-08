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
        POWER power_5v_a -- VCC, GND_1 -- GND
        DATA
            // RPi TX (GPIO14) -> TFMini RXD
            // RPi RX (GPIO15) <- TFMini TXD
            uart[baudrate=115200] tx GPIO14 -- RXD, rx GPIO15 -- TXD;
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
        POWER power_5v_a -- VCC, GND_1 -- GND
        DATA
            uart[baudrate=-1] tx GPIO14 -- RXD, rx GPIO15 -- TXD;
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
        POWER power_5v_a -- VCC, GND_1 -- GND
        DATA
            uart[baudrate=12345] tx GPIO14 -- RXD, rx GPIO15 -- TXD;
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
        POWER power_5v_a -- VCC, GND_1 -- GND
        DATA
            // GPIO23 is not TX
            uart[baudrate=115200] tx GPIO23 -- RXD, rx GPIO15 -- TXD;
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
        POWER power_5v_a -- VCC, GND_1 -- GND
        DATA
            // Connecting Board TX to Peripheral TXD (invalid)
            uart[baudrate=115200] tx GPIO14 -- TXD, rx GPIO15 -- RXD;
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
        POWER power_5v_a -- VCC, GND_1 -- GND
        DATA gpio[mode="output"] GPIO23 -- trigger, gpio[mode="input"] GPIO24 -- echo;
        
    CONNECT Dist2 WITH
        POWER power_5v_b -- VCC, GND_2 -- GND
        DATA gpio[mode="output"] GPIO23 -- trigger, // Conflict on GPIO23
             gpio[mode="input"] GPIO25 -- echo;
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
        POWER power_5v_a -- vcc, GND_1 -- gnd
        DATA i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl;
        
    CONNECT Sensor2 WITH
        POWER power_5v_b -- vcc, GND_2 -- gnd
        DATA i2c[slave_address=0x77] sda GPIO2 -- sda, scl GPIO3 -- scl; // Shared I2C pins OK
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
        POWER power_5v_a -- vcc, GND_1 -- gnd
        DATA i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl;
        
    CONNECT Sensor2 WITH
        POWER power_5v_b -- vcc, GND_2 -- gnd
        DATA i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl; // Same address!
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
        POWER power_5v_a -- vcc, GND_1 -- gnd
        DATA i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl;
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
        POWER power_5v_a -- vcc, GND_1 -- gnd
        DATA i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl;
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
        POWER power_5v_a -- vcc, GND_1 -- gnd
        DATA i2c[slave_address=0x76] sda GPIO2 -- sda, scl GPIO3 -- scl;
    """
    with pytest.raises(TextXSemanticError, match="Broker configuration required"):
        device_mm.model_from_str(model_str)
