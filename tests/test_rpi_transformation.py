import pytest
import os
from demol.lang.device import get_device_mm
from demol.transformations.m2t_rpi import m2t_rpi

def test_rpi_transformation_basic(tmp_path):
    """Test basic RPi transformation with Sensor (BME680) and MQTT Broker."""
    demol_str = """
    DEVICE RPiTest WITH
        description="RPi Test Device",
        author="Tester",
        os=riotos;
    
    USE RaspberryPi_5_8GB;
    USE BME680 [EnvSensor];
    
    NETWORK [WiFi] WITH ssid="ssid", password="pass";
    
    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";
        
    CONNECT EnvSensor WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)
    
    output_dir = tmp_path / "rpi_output"
    m2t_rpi(model, output_dir=str(output_dir))
    
    # Check generated files
    assert (output_dir / "Dockerfile").exists()
    assert (output_dir / "docker-compose.yml").exists()
    assert (output_dir / "requirements.txt").exists()
    assert (output_dir / "install_deps.sh").exists()
    assert (output_dir / "msg.py").exists()
    assert (output_dir / "common.py").exists()
    
    # Check peripheral files
    # Driver module name is bme680_envsensor.py
    assert (output_dir / "bme680_envsensor.py").exists()
    # Node file is envsensor_node.py
    assert (output_dir / "envsensor_node.py").exists()
    
    # Check content of driver file
    driver_content = (output_dir / "bme680_envsensor.py").read_text()
    assert "class BME680_EnvSensor" in driver_content
    assert "import bme680" in driver_content
    assert "import time" in driver_content
    
    # Check content of node file
    node_content = (output_dir / "envsensor_node.py").read_text()
    assert "class BME680Node" in node_content
    # The generated file uses relative import
    assert "from .bme680_envsensor import BME680_EnvSensor" in node_content
    # Topic is used in create_publisher
    assert 'topic="rpitest.sensor.env.envsensor"' in node_content

def test_rpi_transformation_actuator(tmp_path):
    """Test RPi transformation with Actuator (LedGeneric)."""
    demol_str = """
    DEVICE RPiActuatorTest WITH
        description="RPi Actuator Test",
        author="Tester",
        os=riotos;
    
    USE RaspberryPi_5_8GB;
    USE LedGeneric [StatusLed];
    
    NETWORK [WiFi] WITH ssid="ssid", password="pass";
    
    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";
        
    CONNECT StatusLed WITH
        POWER gnd -- GND_1, vcc -- power_3v3_a
        DATA gpio [mode="output"] vin -- GPIO18;
    """
    
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)
    
    output_dir = tmp_path / "rpi_output_actuator"
    m2t_rpi(model, output_dir=str(output_dir))
    
    assert (output_dir / "ledgeneric_statusled.py").exists()
    assert (output_dir / "statusled_node.py").exists()
    
    driver_content = (output_dir / "ledgeneric_statusled.py").read_text()
    assert "class LedGeneric_StatusLed" in driver_content
    assert "PWMLED" in driver_content
    
    node_content = (output_dir / "statusled_node.py").read_text()
    assert "class LedGenericNode" in node_content
    assert "from .ledgeneric_statusled import LedGeneric_StatusLed" in node_content

def test_rpi_transformation_dependencies(tmp_path):
    """Test dependency generation in requirements.txt."""
    demol_str = """
    DEVICE DepTest WITH
        description="Dep Test",
        author="Tester",
        os=riotos;
    
    USE RaspberryPi_5_8GB;
    USE BME680 [EnvSensor];
    
    NETWORK [WiFi] WITH ssid="ssid", password="pass";
    
    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";
        
    CONNECT EnvSensor WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)
    
    output_dir = tmp_path / "rpi_output_deps"
    m2t_rpi(model, output_dir=str(output_dir))
    
    req_content = (output_dir / "requirements.txt").read_text()
    assert "bme680" in req_content
    assert "commlib-py" in req_content # Should be there if template includes it or if it's a common dep

def test_rpi_transformation_proximity(tmp_path):
    """Test RPi transformation with Proximity Sensors (HW006, TCRT5000)."""
    demol_str = """
    DEVICE ProximityTest WITH
        description="Proximity Test",
        author="Tester",
        os=riotos;
    
    USE RaspberryPi_5_8GB;
    USE HW006 [LineSensor];
    USE TCRT5000 [ObstacleSensor];
    
    NETWORK [WiFi] WITH ssid="ssid", password="pass";
    
    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";
        
    CONNECT LineSensor WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA gpio [mode="input"] DO -- GPIO17;
        
    CONNECT ObstacleSensor WITH
        POWER GND -- GND_1, VCC -- power_5v_a
        DATA gpio [mode="input"] D0 -- GPIO27;
    """
    
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)
    
    output_dir = tmp_path / "rpi_output_proximity"
    m2t_rpi(model, output_dir=str(output_dir))
    
    # Check HW006
    assert (output_dir / "hw006_linesensor.py").exists()
    hw006_content = (output_dir / "hw006_linesensor.py").read_text()
    assert '_PIN = "GPIO17"' in hw006_content
    
    assert (output_dir / "tcrt5000_obstaclesensor.py").exists()
    tcrt5000_content = (output_dir / "tcrt5000_obstaclesensor.py").read_text()
    assert '_PIN = "GPIO27"' in tcrt5000_content

def test_rpi_transformation_adc(tmp_path):
    """Test RPi transformation with ADC (ADCDifferentialPi)."""
    demol_str = """
    DEVICE ADCTest WITH
        description="ADC Test",
        author="Tester",
        os=riotos;
    
    USE RaspberryPi_5_8GB;
    USE ADCDifferentialPi [MyADC];
    
    NETWORK [WiFi] WITH ssid="ssid", password="pass";
    
    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";
        
    CONNECT MyADC WITH
        POWER GND -- GND_1, VCC -- power_5v_a
        DATA i2c [slave_address=0x6a] sda SDA -- GPIO2, scl SCL -- GPIO3;
    """
    
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)
    
    output_dir = tmp_path / "rpi_output_adc"
    m2t_rpi(model, output_dir=str(output_dir))
    
    # Check ADC
    assert (output_dir / "adcdifferentialpi_myadc.py").exists()
    adc_content = (output_dir / "adcdifferentialpi_myadc.py").read_text()
    assert 'PRIMARY_SLAVE_ADDRESS = 106' in adc_content # 0x6a = 106
