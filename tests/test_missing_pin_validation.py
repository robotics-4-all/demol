from textx.exceptions import TextXSemanticError
import pytest


def test_missing_pin_on_source(device_mm):
    """
    Test that referencing a non-existent pin on the source component (Peripheral)
    raises a proper validation error and does not crash.
    """
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE LedGeneric[MyLED];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLED WITH
        POWER vcc -- power_3v3_a, gnd -- GND_1
        DATA 
            gpio[mode="output"] vin -- GPIO17, 
            gpio[mode="output"] non_existent_pin -- GPIO18;
    """
    # This should raise a TextXSemanticError about the missing pin, NOT a KeyError
    with pytest.raises(TextXSemanticError, match="Source pin 'non_existent_pin' not found"):
        device_mm.model_from_str(model_str)


def test_missing_pin_on_target(device_mm):
    """
    Test that referencing a non-existent pin on the target component (Board)
    raises a proper validation error and does not crash.
    """
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE LedGeneric[MyLED];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLED WITH
        POWER vcc -- power_3v3_a, gnd -- GND_1
        DATA gpio[mode="output"] vin -- non_existent_pin;
    """
    # This should raise a TextXSemanticError about the missing pin, NOT a KeyError
    with pytest.raises(TextXSemanticError, match="Target pin 'non_existent_pin' not found"):
        device_mm.model_from_str(model_str)


def test_missing_power_pin_on_board(device_mm):
    """
    Test that referencing a non-existent power pin on the board
    raises a proper validation error.
    """
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE LedGeneric[MyLED];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLED WITH
        POWER vcc -- non_existent_power_pin, gnd -- GND_1
        DATA gpio[mode="output"] vin -- GPIO17;
    """
    with pytest.raises(TextXSemanticError, match="Pin 'non_existent_power_pin' not found"):
        device_mm.model_from_str(model_str)


def test_missing_power_pin_on_peripheral(device_mm):
    """
    Test that referencing a non-existent power pin on the peripheral
    raises a proper validation error.
    """
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE LedGeneric[MyLED];
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLED WITH
        POWER vcc -- power_3v3_a, gnd -- GND_1, non_existent_vcc -- power_5v
        DATA gpio[mode="output"] vin -- GPIO17;
    """
    with pytest.raises(TextXSemanticError, match="Pin 'non_existent_vcc' not found"):
        device_mm.model_from_str(model_str)
