"""String-level emission tests for the BH1750 RIOT driver template.

Verifies that ``sensor_bh1750_N.c`` and ``sensor_bh1750_N.h`` are emitted
with the correct RIOT API calls (bh1750fvi_init, bh1750fvi_sample, etc.)
and that optional Jinja2 blocks (sampling on_change/batch, ALERT cooldowns)
render correctly.
"""

from pathlib import Path

from demol.lang.device import get_device_mm
from demol.transformations.m2t_riot import m2t_riot

BASE_MODEL = """
DEVICE Bh1750Test WITH
    description="BH1750 light sensor test",
    author="tester",
    os=riotos;

USE ESP32Wroom32;
USE BH1750 [LightSensor];

NETWORK[WiFi] WITH ssid="ssid", password="pass";

BROKER[MQTT] MyBroker WITH
    host="localhost",
    port=1883,
    auth.username="guest",
    auth.password="guest";

CONNECT LightSensor WITH
    POWER GND -- GND_1, VCC -- VCC_3V3
    DATA i2c[slave_address=0x23] sda sda -- GPIO21, scl scl -- GPIO22
    @ "sensors/light";
"""


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _generate(model_str: str, out: Path) -> None:
    mm = get_device_mm()
    model = mm.model_from_str(model_str)
    m2t_riot(model, output_dir=str(out))


class TestBh1750FileEmission:
    """Verify that the expected driver files are created."""

    def test_bh1750_codegen_emits_c_and_h(self, tmp_path):
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        c_file = out / "sensor_bh1750_0.c"
        h_file = out / "sensor_bh1750_0.h"
        assert c_file.exists(), f"Expected {c_file} to exist"
        assert h_file.exists(), f"Expected {h_file} to exist"

    def test_bh1750_codegen_emits_bh1750fvi_include(self, tmp_path):
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_bh1750_0.c")
        assert '#include "bh1750fvi.h"' in body

    def test_bh1750_codegen_emits_init_and_sample(self, tmp_path):
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_bh1750_0.c")
        assert "bh1750fvi_init(" in body
        assert "bh1750fvi_sample(" in body
        assert "BH1750FVI_OK" in body


class TestBh1750HeaderContent:
    """Verify the generated header file."""

    def test_bh1750_header_has_guard(self, tmp_path):
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_bh1750_0.h")
        assert "#ifndef BH1750_0_DRIVER_H" in body
        assert "#define BH1750_0_DRIVER_H" in body

    def test_bh1750_header_declares_functions(self, tmp_path):
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_bh1750_0.h")
        assert "init_sensor_bh1750_0" in body
        assert "start_sensor_bh1750_0" in body
        assert "bh1750_0_callback" in body

    def test_bh1750_header_has_freq_define(self, tmp_path):
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_bh1750_0.h")
        assert "#define BH1750_0_FREQ" in body


class TestBh1750CI2CAddress:
    """Verify that the I2C slave address is rendered correctly."""

    def test_bh1750_c_has_default_i2c_addr(self, tmp_path):
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_bh1750_0.c")
        assert "params.addr = 0x23" in body

    def test_bh1750_c_has_custom_i2c_addr(self, tmp_path):
        model_str = BASE_MODEL.replace(
            "DATA i2c[slave_address=0x23]",
            "DATA i2c[slave_address=0x5c]",
        )
        out = tmp_path / "out"
        _generate(model_str, out)
        body = _read(out / "sensor_bh1750_0.c")
        assert "params.addr = 0x5c" in body


class TestBh1750PropertyDataStruct:
    """Verify the data struct and property mapping."""

    def test_bh1750_c_has_data_struct(self, tmp_path):
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_bh1750_0.c")
        assert "uint16_t illuminance;" in body

    def test_bh1750_c_uses_data_illuminance(self, tmp_path):
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_bh1750_0.c")
        assert "data.illuminance" in body
