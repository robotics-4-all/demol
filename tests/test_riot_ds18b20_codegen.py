"""Tests for RIOT DS18B20 1-Wire temperature sensor code generation."""

from demol.lang.device import get_device_mm
from demol.transformations.m2t_riot import m2t_riot


def test_riot_ds18b20_basic(tmp_path):
    """Test basic RIOT transformation with DS18B20 GPIO sensor."""
    demol_str = """
    DEVICE RiotDS18B20Test WITH
        description="Riot DS18B20 Basic Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE DS18B20 [TempSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    CONNECT TempSensor WITH
        POWER GND -- GND_1, VCC -- VCC_3V3
        DATA gpio data -- GPIO4;
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_ds18b20_basic"
    m2t_riot(model, output_dir=str(output_dir))

    # Check generated files
    assert (output_dir / "main.c").exists()
    assert (output_dir / "Makefile").exists()
    assert (output_dir / "sensor_ds18b20_0.c").exists()
    assert (output_dir / "sensor_ds18b20_0.h").exists()

    # Check DS18B20 driver content
    ds_content = (output_dir / "sensor_ds18b20_0.c").read_text()
    assert "ds18b20.h" in ds_content
    assert "ds18b20_init" in ds_content
    assert "ds18b20_get_temperature" in ds_content
    assert "GPIO_PIN(0, 32)" in ds_content  # GPIO4 is physical pin 32
    assert "raw_temperature" in ds_content
    assert "Temperature" in ds_content

    # Check header content
    h_content = (output_dir / "sensor_ds18b20_0.h").read_text()
    assert "DS18B20_0_DRIVER_H" in h_content
    assert "DS18B20_0_FREQ" in h_content
    assert "init_sensor_ds18b20_0" in h_content
    assert "start_sensor_ds18b20_0" in h_content


def test_riot_ds18b20_smartconnect(tmp_path):
    """Test RIOT transformation with DS18B20 via SmartConnect."""
    demol_str = """
    DEVICE RiotDS18B20SCTest WITH
        description="Riot DS18B20 SmartConnect Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE DS18B20 [TempSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    SMARTCONNECT TempSensor @ "sensors/temperature";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_ds18b20_sc"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "main.c").exists()
    assert (output_dir / "Makefile").exists()
    assert (output_dir / "sensor_ds18b20_0.c").exists()
    assert (output_dir / "sensor_ds18b20_0.h").exists()

    ds_content = (output_dir / "sensor_ds18b20_0.c").read_text()
    assert "ds18b20_init" in ds_content
    assert "ds18b20_get_temperature" in ds_content
    assert "GPIO_PIN" in ds_content
    assert "raw_temperature" in ds_content


def test_riot_ds18b20_sampling_continuous(tmp_path):
    """Test RIOT DS18B20 code generation with continuous sampling."""
    demol_str = """
    DEVICE RiotDS18B20SamplingTest WITH
        description="Riot DS18B20 Sampling Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE DS18B20 [TempSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    CONNECT TempSensor WITH
        POWER GND -- GND_1, VCC -- VCC_3V3
        DATA gpio data -- GPIO4;

    SAMPLING TempSensor WITH rate = 2 hz;
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_ds18b20_sampling"
    m2t_riot(model, output_dir=str(output_dir))

    assert (output_dir / "sensor_ds18b20_0.h").exists()
    h_content = (output_dir / "sensor_ds18b20_0.h").read_text()
    assert "DS18B20_0_FREQ 500" in h_content  # 2 hz → 500ms period

    assert (output_dir / "sensor_ds18b20_0.c").exists()


def test_riot_ds18b20_sampling_on_change(tmp_path):
    """Test RIOT DS18B20 code generation with on_change sampling mode."""
    demol_str = """
    DEVICE RiotDS18B20OnChangeTest WITH
        description="Riot DS18B20 OnChange Test",
        author="Tester",
        os=riotos;

    USE ESP32Wroom32;
    USE DS18B20 [TempSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    CONNECT TempSensor WITH
        POWER GND -- GND_1, VCC -- VCC_3V3
        DATA gpio data -- GPIO4;

    SAMPLING TempSensor WITH rate = 10 hz, mode = on_change, threshold = 5;
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_ds18b20_onchange"
    m2t_riot(model, output_dir=str(output_dir))

    h_content = (output_dir / "sensor_ds18b20_0.h").read_text()
    assert 'DS18B20_0_SAMPLING_MODE "on_change"' in h_content
    assert "DS18B20_0_THRESHOLD 5" in h_content

    c_content = (output_dir / "sensor_ds18b20_0.c").read_text()
    assert "first_reading" in c_content
    assert "prev_temperature" in c_content
    assert "changed" in c_content
