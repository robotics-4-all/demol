"""Tests for RIOT DHT22 GPIO temperature/humidity sensor code generation."""

from demol.lang.device import get_device_mm
from demol.transformations.m2t_riot import m2t_riot


def test_riot_dht22_basic(tmp_path):
    """Test basic RIOT transformation with DHT22 GPIO sensor."""
    demol_str = """
    DEVICE RiotDHT22BasicTest WITH
        description="Riot DHT22 Basic Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE DHT22 [EnvSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    CONNECT EnvSensor WITH
        POWER GND -- GND_1, VCC -- VCC_3V3
        DATA gpio data -- GPIO4;
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_dht22_basic"
    m2t_riot(model, output_dir=str(output_dir))

    # Check generated files exist
    assert (output_dir / "main.c").exists()
    assert (output_dir / "Makefile").exists()
    assert (output_dir / "sensor_dht22_0.c").exists()
    assert (output_dir / "sensor_dht22_0.h").exists()

    # Check driver C content
    c_content = (output_dir / "sensor_dht22_0.c").read_text()
    assert "periph/gpio.h" in c_content
    assert "DHT22" in c_content
    assert "GPIO_PIN" in c_content
    assert "_dht22_read" in c_content
    assert "data_temperature" in c_content
    assert "data_humidity" in c_content
    assert "xtimer_usleep" in c_content
    assert "Temperature" in c_content
    assert "Humidity" in c_content

    # Check header content
    h_content = (output_dir / "sensor_dht22_0.h").read_text()
    assert "DHT22_0_DRIVER_H" in h_content
    assert "DHT22_0_FREQ" in h_content
    assert "init_sensor_dht22_0" in h_content
    assert "start_sensor_dht22_0" in h_content


def test_riot_dht22_smartconnect(tmp_path):
    """Test RIOT transformation with DHT22 via SmartConnect."""
    demol_str = """
    DEVICE RiotDHT22SCTest WITH
        description="Riot DHT22 SmartConnect Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE DHT22 [EnvSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    SMARTCONNECT EnvSensor @ "sensors/env";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_dht22_sc"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "main.c").exists()
    assert (output_dir / "Makefile").exists()
    assert (output_dir / "sensor_dht22_0.c").exists()
    assert (output_dir / "sensor_dht22_0.h").exists()

    c_content = (output_dir / "sensor_dht22_0.c").read_text()
    assert "_dht22_read" in c_content
    assert "GPIO_PIN" in c_content
    assert "data_temperature" in c_content
    assert "data_humidity" in c_content


def test_riot_dht22_sampling_continuous(tmp_path):
    """Test RIOT DHT22 code generation with continuous sampling."""
    demol_str = """
    DEVICE RiotDHT22SamplingTest WITH
        description="Riot DHT22 Sampling Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE DHT22 [EnvSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    CONNECT EnvSensor WITH
        POWER GND -- GND_1, VCC -- VCC_3V3
        DATA gpio data -- GPIO4;

    SAMPLING EnvSensor WITH rate = 2 hz;
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_dht22_sampling"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "sensor_dht22_0.h").exists()
    h_content = (output_dir / "sensor_dht22_0.h").read_text()
    assert "DHT22_0_FREQ 500" in h_content  # 2 hz -> 500ms period

    assert (output_dir / "sensor_dht22_0.c").exists()


def test_riot_dht22_sampling_on_change(tmp_path):
    """Test RIOT DHT22 code generation with on_change sampling mode."""
    demol_str = """
    DEVICE RiotDHT22OnChangeTest WITH
        description="Riot DHT22 OnChange Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE DHT22 [EnvSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    CONNECT EnvSensor WITH
        POWER GND -- GND_1, VCC -- VCC_3V3
        DATA gpio data -- GPIO4;

    SAMPLING EnvSensor WITH rate = 10 hz, mode = on_change, threshold = 5;
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_dht22_onchange"
    m2t_riot(model, output_dir=str(output_dir))

    h_content = (output_dir / "sensor_dht22_0.h").read_text()
    assert 'DHT22_0_SAMPLING_MODE "on_change"' in h_content
    assert "DHT22_0_THRESHOLD 5" in h_content

    c_content = (output_dir / "sensor_dht22_0.c").read_text()
    assert "first_reading" in c_content
    assert "prev_temperature" in c_content
    assert "prev_humidity" in c_content
    assert "changed" in c_content
