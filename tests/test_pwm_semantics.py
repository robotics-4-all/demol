from textx.exceptions import TextXSemanticError
import pytest
import warnings

# ============================================================================
# PWM Connection Tests (validate_pwm_connection)
# ============================================================================

def test_pwm_valid_connection(device_mm):
    """Test valid PWM connection with all properties."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[frequency=1000, duty_cycle=50] forward -- GPIO18, backward -- GPIO19;
    """
    # Should pass without error
    device_mm.model_from_str(model_str)


def test_pwm_valid_connection_minimal(device_mm):
    """Test valid PWM connection without optional properties."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm forward -- GPIO18, backward -- GPIO19;
    """
    # Should pass without error
    device_mm.model_from_str(model_str)


def test_pwm_with_channel(device_mm):
    """Test PWM connection with channel property."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[frequency=1000, duty_cycle=75, channel=0] forward -- GPIO18, backward -- GPIO19;
    """
    # Should pass without error
    device_mm.model_from_str(model_str)


def test_pwm_led_connection(device_mm):
    """Test PWM connection with LED that has both PWM and GPIO functionality."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE LedGeneric[MyLed];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLed WITH
        POWER
            vcc -- power_3v3_a,
            gnd -- GND_1
        DATA
            pwm[frequency=1000, duty_cycle=50] vin -- GPIO18;
    """
    # Should pass without error (LED pin has both pwm and gpio)
    device_mm.model_from_str(model_str)


def test_pwm_non_pwm_board_pin(device_mm):
    """Test PWM connection to board pin without PWM functionality."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[frequency=1000] forward -- GPIO23, backward -- GPIO24;
    """
    # GPIO23 and GPIO24 are plain GPIO pins without PWM
    with pytest.raises(TextXSemanticError, match="does not have PWM functionality"):
        device_mm.model_from_str(model_str)


def test_pwm_invalid_frequency(device_mm):
    """Test PWM connection with invalid frequency."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[frequency=-100] forward -- GPIO18, backward -- GPIO19;
    """
    with pytest.raises(TextXSemanticError, match="frequency.*must be a positive"):
        device_mm.model_from_str(model_str)


def test_pwm_invalid_duty_cycle_high(device_mm):
    """Test PWM connection with duty cycle > 100."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[duty_cycle=150] forward -- GPIO18, backward -- GPIO19;
    """
    with pytest.raises(TextXSemanticError, match="duty_cycle.*between 0 and 100"):
        device_mm.model_from_str(model_str)


def test_pwm_invalid_duty_cycle_negative(device_mm):
    """Test PWM connection with negative duty cycle."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[duty_cycle=-10] forward -- GPIO18, backward -- GPIO19;
    """
    with pytest.raises(TextXSemanticError, match="duty_cycle.*between 0 and 100"):
        device_mm.model_from_str(model_str)


def test_pwm_invalid_channel(device_mm):
    """Test PWM connection with negative channel."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[channel=-1] forward -- GPIO18, backward -- GPIO19;
    """
    with pytest.raises(TextXSemanticError, match="channel.*non-negative integer"):
        device_mm.model_from_str(model_str)


def test_pwm_invalid_property(device_mm):
    """Test PWM connection with invalid property."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[speed=100] forward -- GPIO18, backward -- GPIO19;
    """
    with pytest.raises(TextXSemanticError, match="Invalid property.*speed"):
        device_mm.model_from_str(model_str)


def test_pwm_pin_conflict_with_gpio(device_mm):
    """Test that PWM and GPIO connections cannot share the same pin."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    USE HCSR04[MyDist];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[frequency=1000] forward -- GPIO18, backward -- GPIO19;
    
    CONNECT MyDist WITH
        POWER
            VCC -- power_5v_b,
            GND -- GND_2
        DATA
            gpio[mode="output"] trigger -- GPIO18,
            gpio[mode="input"] echo -- GPIO24;
    """
    with pytest.raises(TextXSemanticError, match="Pin conflict.*GPIO18"):
        device_mm.model_from_str(model_str)


def test_pwm_multiple_connections_different_pins(device_mm):
    """Test multiple PWM connections on different pins."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[Motor1];
    USE LedGeneric[Led1];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT Motor1 WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[frequency=1000, duty_cycle=50] forward -- GPIO18, backward -- GPIO19;
    
    CONNECT Led1 WITH
        POWER
            vcc -- power_3v3_a,
            gnd -- GND_2
        DATA
            pwm[frequency=500, duty_cycle=75] vin -- GPIO13;
    """
    # Should pass - different pins
    device_mm.model_from_str(model_str)


def test_pwm_boundary_duty_cycle_zero(device_mm):
    """Test PWM connection with duty cycle = 0."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[duty_cycle=0] forward -- GPIO18, backward -- GPIO19;
    """
    # Should pass - 0 is valid
    device_mm.model_from_str(model_str)


def test_pwm_boundary_duty_cycle_hundred(device_mm):
    """Test PWM connection with duty cycle = 100."""
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE MotorGeneric[MyMotor];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyMotor WITH
        POWER
            vcc -- power_5v_a,
            gnd -- GND_1
        DATA
            pwm[duty_cycle=100] forward -- GPIO18, backward -- GPIO19;
    """
    # Should pass - 100 is valid
    device_mm.model_from_str(model_str)
