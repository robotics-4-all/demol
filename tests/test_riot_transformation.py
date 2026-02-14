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
