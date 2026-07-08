"""Syntax-level integrity tests for Zephyr BME280 code generation.

Verifies the Zephyr backend produces a complete app/ tree with a
bme280.c driver, that the emitted C contains the expected Zephyr
sensor API calls, and that the prj.conf enables the BME280 driver.
"""

from pathlib import Path
from textwrap import dedent

import pytest

from demol.transformations.m2t_zephyr import m2t_zephyr

SYNTHETIC_BME280_MODEL = dedent("""\
    DEVICE SyntheticBme280 WITH description="bme280 codegen test", author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME280[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_3v3
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme280";
    """)


def test_bme280_app_tree_is_emitted(device_mm, tmp_path):
    """Generating a BME280 model produces the expected Zephyr app tree."""
    model = device_mm.model_from_str(SYNTHETIC_BME280_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    app_dir = tmp_path / "app"
    assert app_dir.is_dir(), "Missing app/ directory"

    assert (app_dir / "CMakeLists.txt").is_file(), "Missing CMakeLists.txt"
    assert (app_dir / "prj.conf").is_file(), "Missing prj.conf"
    assert (app_dir / "src" / "main.c").is_file(), "Missing src/main.c"
    assert (app_dir / "src" / "bme280.c").is_file(), "Missing src/bme280.c"

    overlays = list((app_dir / "boards").glob("*.overlay"))
    assert overlays, "Missing board overlay"


def test_bme280_driver_uses_zephyr_sensor_api(device_mm, tmp_path):
    """The generated bme280.c contains Zephyr sensor API calls."""
    model = device_mm.model_from_str(SYNTHETIC_BME280_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    bme280_c = tmp_path / "app" / "src" / "bme280.c"
    assert bme280_c.is_file()

    body = bme280_c.read_text(encoding="utf-8")
    assert "sensor_sample_fetch" in body, "Missing sensor_sample_fetch"
    assert "DEVICE_DT_GET" in body, "Missing DEVICE_DT_GET"
    assert "bosch_bme280" in body, "Missing bosch_bme280 compatible"
    assert "sensor_channel_get" in body, "Missing sensor_channel_get"
    assert "sensor_value_to_double" in body, "Missing sensor_value_to_double"
    assert "struct bme280_data" in body, "Missing bme280_data struct"


def test_bme280_prj_conf_has_kconfig(device_mm, tmp_path):
    """The generated prj.conf enables CONFIG_BME280."""
    model = device_mm.model_from_str(SYNTHETIC_BME280_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    prj_conf = (tmp_path / "app" / "prj.conf").read_text(encoding="utf-8")
    assert "CONFIG_BME280=y" in prj_conf, "Missing CONFIG_BME280 in prj.conf"
