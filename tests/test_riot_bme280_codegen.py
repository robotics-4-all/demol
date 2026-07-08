"""RIOT code generation tests for the BME280 peripheral driver.

Verifies that the sensor_bme280.c.j2 / sensor_bme280.h.j2 templates
produce correct C code with the bmx280 driver API.
"""

from demol.lang.device import get_device_mm
from demol.transformations.m2t_riot import m2t_riot


def test_bme280_codegen_basic(tmp_path):
    """BME280 RIOT codegen produces all expected files."""
    demol_str = """
    DEVICE BME280Test WITH
        description="BME280 on ESP32",
        author="Test",
        os=riotos;

    USE ESP32Wroom32;
    USE BME280 [EnvSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    CONNECT EnvSensor WITH
        POWER
            gnd -- GND_1,
            vcc -- VCC_3V3
        DATA
            i2c [slave_address=0x76] sda sda -- GPIO21, scl scl -- GPIO22
        @ "sensors/env/bme280";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_bme280"
    m2t_riot(model, output_dir=str(output_dir))

    # Common infrastructure files
    assert (output_dir / "main.c").exists()
    assert (output_dir / "Makefile").exists()
    assert (output_dir / "mqtt_broker.c").exists()
    assert (output_dir / "mqtt_broker.h").exists()
    assert (output_dir / "json_handler.c").exists()
    assert (output_dir / "json_handler.h").exists()
    assert (output_dir / "build_docker.sh").exists()

    # BME280 peripheral driver
    assert (output_dir / "sensor_bme280_0.c").exists()
    assert (output_dir / "sensor_bme280_0.h").exists()


def test_bme280_codegen_content(tmp_path):
    """BME280 generated C uses correct bmx280 API, I2C config, and data struct."""
    demol_str = """
    DEVICE BME280ContentTest WITH
        description="BME280 content check",
        author="Test",
        os=riotos;

    USE ESP32Wroom32;
    USE BME280 [EnvSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    CONNECT EnvSensor WITH
        POWER
            gnd -- GND_1,
            vcc -- VCC_3V3
        DATA
            i2c [slave_address=0x76] sda sda -- GPIO21, scl scl -- GPIO22
        @ "sensors/env/bme280";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_bme280_content"
    m2t_riot(model, output_dir=str(output_dir))

    c_content = (output_dir / "sensor_bme280_0.c").read_text()

    # Correct header include (bmx280.h, not bme680.h)
    assert '#include "bmx280.h"' in c_content

    # I2C device and address configuration
    assert "params.i2c_dev = I2C_DEV(0);" in c_content
    assert "params.i2c_addr = 0x76;" in c_content

    # bmx280_t device struct (not bme680_t)
    assert "bmx280_t bme280_0_dev;" in c_content

    # bmx280_params_t (not bme680_params_t)
    assert "bmx280_params_t params;" in c_content

    # Run mode (new param vs bme680 — no gas measurement)
    assert "params.run_mode = BMX280_MODE_NORMAL;" in c_content

    # Oversample configuration
    assert "params.temp_oversample = BMX280_OSRS_X2;" in c_content
    assert "params.press_oversample = BMX280_OSRS_X4;" in c_content
    assert "params.humid_oversample = BMX280_OSRS_X1;" in c_content

    # Filter
    assert "params.filter = BMX280_FILTER_2;" in c_content

    # Uses BMX280_OK, not BME680_OK
    assert "BMX280_OK" in c_content

    # Use local data struct for temperature/pressure/humidity
    assert "struct {" in c_content
    assert "int32_t temperature;" in c_content
    assert "uint32_t pressure;" in c_content
    assert "int32_t humidity;" in c_content
    assert "} data;" in c_content

    # Read functions
    assert "bmx280_read_temperature(&bme280_0_dev)" in c_content
    assert "bmx280_read_pressure(&bme280_0_dev)" in c_content
    assert "bme280_read_humidity(&bme280_0_dev)" in c_content

    # Error check for temperature
    assert "data.temperature != INT16_MIN" in c_content

    # JSON payload keys
    assert 'JSON_KEY, "Temperature", JSON_INT, data.temperature' in c_content
    assert 'JSON_KEY, "Pressure", JSON_INT, data.pressure' in c_content
    assert 'JSON_KEY, "Humidity", JSON_INT, data.humidity' in c_content

    # Header file check
    h_content = (output_dir / "sensor_bme280_0.h").read_text()
    assert "BME280_0_DRIVER_H" in h_content
    assert "init_sensor_bme280_0" in h_content
    assert "start_sensor_bme280_0" in h_content
    assert "BME280_0_FREQ" in h_content


def test_bme280_makefile_deps(tmp_path):
    """Makefile includes bme280_i2c module dependency."""
    demol_str = """
    DEVICE BME280DepsTest WITH
        description="BME280 dependency check",
        author="Test",
        os=riotos;

    USE ESP32Wroom32;
    USE BME280 [EnvSensor];

    NETWORK [WiFi] WITH ssid="ssid", password="pass";

    BROKER [MQTT] MyBroker WITH
        host="localhost",
        port=1883;

    CONNECT EnvSensor WITH
        POWER
            gnd -- GND_1,
            vcc -- VCC_3V3
        DATA
            i2c [slave_address=0x76] sda sda -- GPIO21, scl scl -- GPIO22
        @ "sensors/env/bme280";
    """

    mm = get_device_mm()
    model = mm.model_from_str(demol_str)

    output_dir = tmp_path / "riot_bme280_deps"
    m2t_riot(model, output_dir=str(output_dir))

    makefile = (output_dir / "Makefile").read_text()
    assert "USEMODULE += bme280_i2c" in makefile
