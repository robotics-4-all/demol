from textx.exceptions import TextXSemanticError
import pytest

def test_optional_network_valid(device_mm):
    # Model without network and without broker/remote is valid
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE LedGeneric[MyLED];
    
    CONNECT MyLED WITH
        POWER
            power_3v3_a -- vcc,
            GND_1 -- gnd
        DATA
            gpio[mode="output"] GPIO17 -- vin;
    """
    # Should not raise any error
    device_mm.model_from_str(model_str)

def test_missing_network_with_broker(device_mm):
    # Model without network but with broker should fail
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE LedGeneric[MyLED];
    
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLED WITH
        POWER
            power_3v3_a -- vcc,
            GND_1 -- gnd
        DATA
            gpio[mode="output"] GPIO17 -- vin;
    """
    with pytest.raises(TextXSemanticError, match=r".*WF-Network-Requirements.*"):
        device_mm.model_from_str(model_str)

def test_missing_network_with_remote(device_mm):
    # Model without network but with remote endpoint should fail
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE LedGeneric[MyLED];
    
    CONNECT MyLED WITH
        POWER
            power_3v3_a -- vcc,
            GND_1 -- gnd
        DATA
            gpio[mode="output"] GPIO17 -- vin
        @ "led/control";
    """
    # Note: validate_broker_requirements will also fail here because no broker is defined
    # but validate_network_requirements is called after it.
    
    with pytest.raises(TextXSemanticError) as excinfo:
        device_mm.model_from_str(model_str)
    
    assert "WF-Broker-Requirements" in str(excinfo.value) or "WF-Network-Requirements" in str(excinfo.value)

def test_network_with_broker_valid(device_mm):
    # Model with network and broker is valid
    model_str = """
    DEVICE TestDevice WITH description="Test", author="Test", os=raspbian;
    USE RaspberryPi_4B_4GB;
    USE LedGeneric[MyLED];
    
    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] MyBroker WITH host="localhost", port=1883;
    
    CONNECT MyLED WITH
        POWER
            power_3v3_a -- vcc,
            GND_1 -- gnd
        DATA
            gpio[mode="output"] GPIO17 -- vin
        @ "led/control";
    """
    device_mm.model_from_str(model_str)
