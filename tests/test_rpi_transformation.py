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
    assert "commlib-py" in req_content  # Should be there if template includes it or if it's a common dep


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
    assert "PRIMARY_SLAVE_ADDRESS = 106" in adc_content  # 0x6a = 106


def test_rpi_transformation_sampling_continuous(tmp_path):
    """Test RPi code generation with SAMPLING continuous mode."""
    demol_str = """
    DEVICE SamplingTest WITH
        description="Sampling Test",
        author="Tester",
        os=raspbian;

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

    SAMPLING EnvSensor WITH rate = 5 hz, mode = continuous;
    """
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "rpi_sampling_continuous"
    m2t_rpi(model, output_dir=str(output_dir))

    node_content = (output_dir / "envsensor_node.py").read_text()
    assert "_FREQUENCY = 5.0" in node_content
    assert '_SAMPLING_MODE = "continuous"' in node_content
    assert "_send()" in node_content


def test_rpi_transformation_sampling_on_change(tmp_path):
    """Test RPi code generation with SAMPLING on_change mode."""
    demol_str = """
    DEVICE SamplingTest WITH
        description="Sampling Test",
        author="Tester",
        os=raspbian;

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

    SAMPLING EnvSensor WITH rate = 10 hz, mode = on_change, threshold = 0.5;
    """
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "rpi_sampling_on_change"
    m2t_rpi(model, output_dir=str(output_dir))

    node_content = (output_dir / "envsensor_node.py").read_text()
    assert "_FREQUENCY = 10.0" in node_content
    assert '_SAMPLING_MODE = "on_change"' in node_content
    assert "_THRESHOLD = 0.5" in node_content
    assert "_has_changed" in node_content
    assert "_last_data" in node_content


def test_rpi_transformation_sampling_batch(tmp_path):
    """Test RPi code generation with SAMPLING batch mode."""
    demol_str = """
    DEVICE SamplingTest WITH
        description="Sampling Test",
        author="Tester",
        os=raspbian;

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

    SAMPLING EnvSensor WITH rate = 20 hz, mode = batch, buffer = 10;
    """
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "rpi_sampling_batch"
    m2t_rpi(model, output_dir=str(output_dir))

    node_content = (output_dir / "envsensor_node.py").read_text()
    assert "_FREQUENCY = 20.0" in node_content
    assert '_SAMPLING_MODE = "batch"' in node_content
    assert "_BATCH_SIZE = 10" in node_content
    assert "_send_batch" in node_content
    assert "_batch" in node_content


def test_rpi_transformation_no_sampling_uses_default(tmp_path):
    """Test RPi code generation without SAMPLING uses attribute frequency."""
    demol_str = """
    DEVICE NoSamplingTest WITH
        description="No Sampling Test",
        author="Tester",
        os=raspbian;

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

    output_dir = tmp_path / "rpi_no_sampling"
    m2t_rpi(model, output_dir=str(output_dir))

    node_content = (output_dir / "envsensor_node.py").read_text()
    assert '_SAMPLING_MODE = "continuous"' in node_content
    assert "_THRESHOLD" not in node_content
    assert "_BATCH_SIZE" not in node_content


def test_rpi_smartconnect_i2c_sensor(tmp_path):
    """Test RPi transformation with SmartConnect I2C sensor (BME680)."""
    demol_str = """
    DEVICE SCTest WITH
        description="SmartConnect I2C Test",
        author="Tester",
        os=raspbian;

    USE RaspberryPi_5_8GB;
    USE BME680 [EnvSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";

    SMARTCONNECT EnvSensor @ "sensors/env";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "rpi_sc_i2c"
    m2t_rpi(model, output_dir=str(output_dir))

    # Check generated files
    assert (output_dir / "bme680_envsensor.py").exists()
    assert (output_dir / "envsensor_node.py").exists()
    assert (output_dir / "Dockerfile").exists()
    assert (output_dir / "docker-compose.yml").exists()

    # Check driver content — SmartConnect resolves I2C to GPIO2/GPIO3
    driver_content = (output_dir / "bme680_envsensor.py").read_text()
    assert "class BME680_EnvSensor" in driver_content
    assert "import bme680" in driver_content
    assert "_PRIMARY_ADDRESS = 118" in driver_content  # 0x76 = 118

    # Check node content
    node_content = (output_dir / "envsensor_node.py").read_text()
    assert "from .bme680_envsensor import BME680_EnvSensor" in node_content
    assert 'topic="sensors/env"' in node_content


def test_rpi_smartconnect_gpio_sensor(tmp_path):
    """Test RPi transformation with SmartConnect GPIO sensor (HCSR04)."""
    demol_str = """
    DEVICE SCTest WITH
        description="SmartConnect GPIO Sensor Test",
        author="Tester",
        os=raspbian;

    USE RaspberryPi_5_8GB;
    USE HCSR04 [DistSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";

    SMARTCONNECT DistSensor @ "sensors/distance";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "rpi_sc_gpio_sensor"
    m2t_rpi(model, output_dir=str(output_dir))

    assert (output_dir / "hcsr04_distsensor.py").exists()
    assert (output_dir / "distsensor_node.py").exists()

    # SmartConnect assigns GPIO2 (echo) and GPIO3 (trigger) deterministically
    driver_content = (output_dir / "hcsr04_distsensor.py").read_text()
    assert "class HCSR04_DistSensor" in driver_content
    assert '_TRIGGER_PIN = "GPIO3"' in driver_content
    assert '_ECHO_PIN = "GPIO2"' in driver_content


def test_rpi_smartconnect_gpio_actuator(tmp_path):
    """Test RPi transformation with SmartConnect GPIO/PWM actuator (LedGeneric)."""
    demol_str = """
    DEVICE SCTest WITH
        description="SmartConnect Actuator Test",
        author="Tester",
        os=raspbian;

    USE RaspberryPi_5_8GB;
    USE LedGeneric [StatusLed];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";

    SMARTCONNECT StatusLed @ "actuators/led";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "rpi_sc_actuator"
    m2t_rpi(model, output_dir=str(output_dir))

    assert (output_dir / "ledgeneric_statusled.py").exists()
    assert (output_dir / "statusled_node.py").exists()

    # SmartConnect assigns GPIO18 (first PWM pin) deterministically
    driver_content = (output_dir / "ledgeneric_statusled.py").read_text()
    assert "class LedGeneric_StatusLed" in driver_content
    assert "PWMLED" in driver_content
    assert '_PIN = "GPIO18"' in driver_content


def test_rpi_smartconnect_mixed(tmp_path):
    """Test RPi transformation with manual CONNECT + SmartConnect in same model."""
    demol_str = """
    DEVICE SCMixedTest WITH
        description="Mixed CONNECT + SmartConnect",
        author="Tester",
        os=raspbian;

    USE RaspberryPi_5_8GB;
    USE BME680 [EnvSensor], HCSR04 [DistSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";

    CONNECT EnvSensor WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA i2c [slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
        @ "sensors/env";

    SMARTCONNECT DistSensor @ "sensors/distance";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "rpi_sc_mixed"
    m2t_rpi(model, output_dir=str(output_dir))

    # Manual CONNECT peripheral
    assert (output_dir / "bme680_envsensor.py").exists()
    driver_bme = (output_dir / "bme680_envsensor.py").read_text()
    assert "_PRIMARY_ADDRESS = 118" in driver_bme

    # SmartConnect peripheral — avoids GPIO2/GPIO3 (used by manual CONNECT)
    assert (output_dir / "hcsr04_distsensor.py").exists()
    driver_hcsr = (output_dir / "hcsr04_distsensor.py").read_text()
    assert '_ECHO_PIN = "GPIO4"' in driver_hcsr
    assert '_TRIGGER_PIN = "GPIO14"' in driver_hcsr

    # Both node files exist with correct topics
    node_env = (output_dir / "envsensor_node.py").read_text()
    assert 'topic="sensors/env"' in node_env
    node_dist = (output_dir / "distsensor_node.py").read_text()
    assert 'topic="sensors/distance"' in node_dist


def test_rpi_smartconnect_multi_peripheral(tmp_path):
    """Test RPi transformation with all-SmartConnect multi-peripheral model."""
    demol_str = """
    DEVICE SCMultiTest WITH
        description="All SmartConnect Multi-Peripheral",
        author="Tester",
        os=raspbian;

    USE RaspberryPi_5_8GB;
    USE BME680 [EnvSensor], HCSR04 [DistSensor], LedGeneric [StatusLed];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";

    SMARTCONNECT EnvSensor @ "sensors/env";
    SMARTCONNECT DistSensor @ "sensors/distance";
    SMARTCONNECT StatusLed @ "actuators/led";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "rpi_sc_multi"
    m2t_rpi(model, output_dir=str(output_dir))

    # All 6 peripheral files exist (3 drivers + 3 nodes)
    assert (output_dir / "bme680_envsensor.py").exists()
    assert (output_dir / "envsensor_node.py").exists()
    assert (output_dir / "hcsr04_distsensor.py").exists()
    assert (output_dir / "distsensor_node.py").exists()
    assert (output_dir / "ledgeneric_statusled.py").exists()
    assert (output_dir / "statusled_node.py").exists()

    # Infrastructure files
    assert (output_dir / "Dockerfile").exists()
    assert (output_dir / "docker-compose.yml").exists()
    assert (output_dir / "requirements.txt").exists()

    # BME680 — I2C, GPIO2/GPIO3, slave_address=0x76
    driver_bme = (output_dir / "bme680_envsensor.py").read_text()
    assert "_PRIMARY_ADDRESS = 118" in driver_bme

    # HCSR04 — GPIO, avoids GPIO2/GPIO3 (I2C, not available for GPIO)
    driver_hcsr = (output_dir / "hcsr04_distsensor.py").read_text()
    assert '_ECHO_PIN = "GPIO4"' in driver_hcsr
    assert '_TRIGGER_PIN = "GPIO14"' in driver_hcsr

    # LedGeneric — PWM, GPIO18 (first PWM-capable pin)
    driver_led = (output_dir / "ledgeneric_statusled.py").read_text()
    assert '_PIN = "GPIO18"' in driver_led


def test_rpi_transformation_sampling_on_demand(tmp_path):
    """Test RPi code generation with SAMPLING on_demand mode.

    Verifies that a read_on_demand() method is emitted for RPC-style
    external invocation.
    """
    demol_str = """
    DEVICE SamplingTest WITH
        description="Sampling Test",
        author="Tester",
        os=raspbian;

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

    SAMPLING EnvSensor WITH rate = 5 hz, mode = on_demand;
    """
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "rpi_sampling_on_demand"
    m2t_rpi(model, output_dir=str(output_dir))

    node_content = (output_dir / "envsensor_node.py").read_text()
    assert "_FREQUENCY = 5.0" in node_content
    assert '_SAMPLING_MODE = "on_demand"' in node_content
    assert "def read_on_demand(self):" in node_content
    assert "self._read()" in node_content
    assert "self._send()" in node_content
