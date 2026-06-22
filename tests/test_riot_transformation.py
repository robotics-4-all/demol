from demol.lang.device import get_device_mm
from demol.transformations.m2t_riot import m2t_riot


def test_riot_transformation_basic(tmp_path):
    """Test basic Riot transformation with Sensor (BME680) and Actuator (LedGeneric)."""
    demol_str = """
    DEVICE RiotTest WITH
        description="Riot Test Device",
        author="Tester",
        os=riotos;
    
    USE ESP32Wroom32;
    USE BME680 [EnvSensor];
    USE LedGeneric [StatusLed];
    
    NETWORK [WiFi] WITH ssid="ssid", password="pass";
    
    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";
        
    CONNECT EnvSensor WITH
        POWER gnd -- GND_1, vcc -- VCC_5V
        DATA i2c [slave_address=0x77] sda sda -- GPIO21, scl scl -- GPIO22;
        
    CONNECT StatusLed WITH
        POWER gnd -- GND_1, vcc -- VCC_3V3
        DATA gpio [mode="output"] vin -- GPIO18;
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_output"
    m2t_riot(model, output_dir=str(output_dir))

    # Check generated files
    assert (output_dir / "main.c").exists()
    assert (output_dir / "Makefile").exists()
    assert (output_dir / "mqtt_broker.c").exists()
    assert (output_dir / "mqtt_broker.h").exists()
    assert (output_dir / "json_handler.c").exists()
    assert (output_dir / "json_handler.h").exists()
    assert (output_dir / "build_docker.sh").exists()

    # Check peripheral files
    # ESP32Wroom32 pins: GPIO21 is physical 25, GPIO22 is physical 22, GPIO18 is physical 28
    # BME680 is index 0, LedGeneric is index 1
    assert (output_dir / "sensor_bme680_0.c").exists()
    assert (output_dir / "sensor_bme680_0.h").exists()
    assert (output_dir / "actuator_led_1.c").exists()
    assert (output_dir / "actuator_led_1.h").exists()

    # Check content of BME680 driver
    bme_content = (output_dir / "sensor_bme680_0.c").read_text()
    # GPIO21 is SDA-0, GPIO22 is SCL-0. Bus should be 0.
    assert "params.intf.i2c.dev = I2C_DEV(0);" in bme_content
    # 0x77 slave address
    assert "params.intf.i2c.addr = 0x77;" in bme_content

    # Check content of LED driver
    led_content = (output_dir / "actuator_led_1.c").read_text()
    # GPIO18 is physical pin 28
    assert "GPIO_PIN(0, 28)" in led_content


def test_riot_transformation_proximity(tmp_path):
    """Test Riot transformation with SRF04 sensor."""
    demol_str = """
    DEVICE RiotProximityTest WITH
        description="Riot Proximity Test",
        author="Tester",
        os=riotos;
    
    USE ESP32Wroom32;
    USE SRF04 [Sonar];
    
    NETWORK [WiFi] WITH ssid="ssid", password="pass";
    
    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;
        
    CONNECT Sonar WITH
        POWER gnd -- GND_1, vcc -- VCC_5V
        DATA gpio trigger -- GPIO4, echo -- GPIO2;
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_output_proximity"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "sensor_srf04_0.c").exists()
    srf_content = (output_dir / "sensor_srf04_0.c").read_text()
    # GPIO4 is physical 32, GPIO2 is physical 34
    assert "params.trigger = GPIO_PIN(0, 32);" in srf_content
    assert "params.echo = GPIO_PIN(0, 34);" in srf_content


def test_riot_transformation_ws281x(tmp_path):
    """Test Riot transformation with WS281X actuator."""
    demol_str = """
    DEVICE RiotWS281XTest WITH
        description="Riot WS281X Test",
        author="Tester",
        os=riotos;
    
    USE ESP32Wroom32;
    USE WS281X [Strip] WITH num_leds=30;
    
    NETWORK [WiFi] WITH ssid="ssid", password="pass";
    
    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;
        
    CONNECT Strip WITH
        POWER gnd -- GND_1, vcc -- VCC_5V
        DATA gpio data_in -- GPIO5;
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_output_ws281x"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "actuator_ws281x_0.c").exists()
    ws_content = (output_dir / "actuator_ws281x_0.c").read_text()
    # GPIO5 is physical 29
    assert "params.pin = GPIO_PIN(0, 29);" in ws_content
    # num_leds=30
    assert "params.numof = 30;" in ws_content
    assert "static uint8_t ws281x_0_buf[30 * WS281X_BYTES_PER_DEVICE];" in ws_content


def test_riot_transformation_hw006(tmp_path):
    """Test Riot transformation with HW006 proximity sensor."""
    demol_str = """
    DEVICE RiotHW006Test WITH
        description="Riot HW006 Test",
        author="Tester",
        os=riotos;
    
    USE ESP32Wroom32;
    USE HW006 [Prox];
    
    NETWORK [WiFi] WITH ssid="ssid", password="pass";
    
    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;
        
    CONNECT Prox WITH
        POWER gnd -- GND_1, vcc -- VCC_5V
        DATA gpio DO -- GPIO4;
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_output_hw006"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "sensor_hw006_0.c").exists()
    hw_content = (output_dir / "sensor_hw006_0.c").read_text()
    # GPIO4 is physical 32
    assert "GPIO_PIN(0, 32)" in hw_content


def test_riot_transformation_sampling_continuous(tmp_path):
    """Test RiotOS code generation with SAMPLING continuous mode."""
    demol_str = """
    DEVICE RiotSamplingTest WITH
        description="Riot Sampling Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE BME680 [EnvSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";

    CONNECT EnvSensor WITH
        POWER gnd -- GND_1, vcc -- VCC_5V
        DATA i2c [slave_address=0x77] sda sda -- GPIO21, scl scl -- GPIO22;

    SAMPLING EnvSensor WITH rate = 2 hz;
    """
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_sampling_continuous"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "sensor_bme680_0.h").exists()
    h_content = (output_dir / "sensor_bme680_0.h").read_text()
    assert "BME680_0_FREQ 500" in h_content

    assert (output_dir / "sensor_bme680_0.c").exists()


def test_riot_transformation_sampling_on_change(tmp_path):
    """Test RiotOS code generation with SAMPLING on_change mode."""
    demol_str = """
    DEVICE RiotOnChangeTest WITH
        description="Riot OnChange Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE SRF04 [Sonar];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    CONNECT Sonar WITH
        POWER gnd -- GND_1, vcc -- VCC_5V
        DATA gpio trigger -- GPIO4, echo -- GPIO2;

    SAMPLING Sonar WITH rate = 10 hz, mode = on_change, threshold = 5;
    """
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_sampling_on_change"
    m2t_riot(model, output_dir=str(output_dir))

    h_content = (output_dir / "sensor_srf04_0.h").read_text()
    assert 'SRF04_0_SAMPLING_MODE "on_change"' in h_content
    assert "SRF04_0_THRESHOLD 5" in h_content

    c_content = (output_dir / "sensor_srf04_0.c").read_text()
    assert "prev_dist" in c_content
    assert "changed" in c_content


def test_riot_transformation_sampling_batch(tmp_path):
    """Test RiotOS code generation with SAMPLING batch mode."""
    demol_str = """
    DEVICE RiotBatchTest WITH
        description="Riot Batch Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE BME680 [EnvSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";

    CONNECT EnvSensor WITH
        POWER gnd -- GND_1, vcc -- VCC_5V
        DATA i2c [slave_address=0x77] sda sda -- GPIO21, scl scl -- GPIO22;

    SAMPLING EnvSensor WITH rate = 50 hz, mode = batch, buffer = 20;
    """
    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_sampling_batch"
    m2t_riot(model, output_dir=str(output_dir))

    h_content = (output_dir / "sensor_bme680_0.h").read_text()
    assert 'BME680_0_SAMPLING_MODE "batch"' in h_content
    assert "BME680_0_BATCH_SIZE 20" in h_content

    c_content = (output_dir / "sensor_bme680_0.c").read_text()
    assert "batch_count" in c_content


def test_riot_smartconnect_i2c_sensor(tmp_path):
    """Test Riot transformation with SmartConnect I2C sensor (BME680)."""
    demol_str = """
    DEVICE SCTest WITH
        description="SmartConnect I2C Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
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

    output_dir = tmp_path / "riot_sc_i2c"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "main.c").exists()
    assert (output_dir / "Makefile").exists()
    assert (output_dir / "sensor_bme680_0.c").exists()
    assert (output_dir / "sensor_bme680_0.h").exists()

    bme_content = (output_dir / "sensor_bme680_0.c").read_text()
    assert "params.intf.i2c.dev = I2C_DEV(0);" in bme_content
    assert "params.intf.i2c.addr = 0x76;" in bme_content


def test_riot_smartconnect_gpio_sensor(tmp_path):
    """Test Riot transformation with SmartConnect GPIO sensor (SRF04)."""
    demol_str = """
    DEVICE SCTest WITH
        description="SmartConnect GPIO Sensor Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE SRF04 [Sonar];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    SMARTCONNECT Sonar @ "sensors/distance";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_sc_gpio_sensor"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "sensor_srf04_0.c").exists()
    assert (output_dir / "sensor_srf04_0.h").exists()

    srf_content = (output_dir / "sensor_srf04_0.c").read_text()
    assert "params.trigger = GPIO_PIN(0, 2);" in srf_content
    assert "params.echo = GPIO_PIN(0, 3);" in srf_content


def test_riot_smartconnect_gpio_actuator(tmp_path):
    """Test Riot transformation with SmartConnect GPIO/PWM actuator (LedGeneric)."""
    demol_str = """
    DEVICE SCTest WITH
        description="SmartConnect Actuator Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE LedGeneric [StatusLed];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    SMARTCONNECT StatusLed @ "actuators/led";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_sc_actuator"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "actuator_led_0.c").exists()
    assert (output_dir / "actuator_led_0.h").exists()

    led_content = (output_dir / "actuator_led_0.c").read_text()
    assert "GPIO_PIN(0, 30)" in led_content


def test_riot_smartconnect_mixed(tmp_path):
    """Test Riot transformation with manual CONNECT + SmartConnect in same model."""
    demol_str = """
    DEVICE SCMixedTest WITH
        description="Mixed CONNECT + SmartConnect",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE BME680 [EnvSensor], LedGeneric [StatusLed];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";

    CONNECT EnvSensor WITH
        POWER gnd -- GND_1, vcc -- VCC_5V
        DATA i2c [slave_address=0x77] sda sda -- GPIO21, scl scl -- GPIO22;

    SMARTCONNECT StatusLed @ "actuators/led";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_sc_mixed"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "sensor_bme680_0.c").exists()
    bme_content = (output_dir / "sensor_bme680_0.c").read_text()
    assert "params.intf.i2c.dev = I2C_DEV(0);" in bme_content
    assert "params.intf.i2c.addr = 0x77;" in bme_content

    assert (output_dir / "actuator_led_1.c").exists()
    led_content = (output_dir / "actuator_led_1.c").read_text()
    assert "GPIO_PIN(0, 30)" in led_content


def test_riot_smartconnect_multi_peripheral(tmp_path):
    """Test Riot transformation with all-SmartConnect multi-peripheral model."""
    demol_str = """
    DEVICE SCMultiTest WITH
        description="All SmartConnect Multi-Peripheral",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE BME680 [EnvSensor], SRF04 [Sonar], LedGeneric [StatusLed];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883,
        auth.username="user",
        auth.password="pass";

    SMARTCONNECT EnvSensor @ "sensors/env";
    SMARTCONNECT Sonar @ "sensors/distance";
    SMARTCONNECT StatusLed @ "actuators/led";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_sc_multi"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "sensor_bme680_0.c").exists()
    assert (output_dir / "sensor_bme680_0.h").exists()
    assert (output_dir / "sensor_srf04_1.c").exists()
    assert (output_dir / "sensor_srf04_1.h").exists()
    assert (output_dir / "actuator_led_2.c").exists()
    assert (output_dir / "actuator_led_2.h").exists()
    assert (output_dir / "main.c").exists()
    assert (output_dir / "Makefile").exists()

    bme_content = (output_dir / "sensor_bme680_0.c").read_text()
    assert "params.intf.i2c.dev = I2C_DEV(0);" in bme_content
    assert "params.intf.i2c.addr = 0x76;" in bme_content

    srf_content = (output_dir / "sensor_srf04_1.c").read_text()
    assert "params.trigger = GPIO_PIN(0, 2);" in srf_content
    assert "params.echo = GPIO_PIN(0, 3);" in srf_content

    led_content = (output_dir / "actuator_led_2.c").read_text()
    assert "GPIO_PIN(0, 30)" in led_content
