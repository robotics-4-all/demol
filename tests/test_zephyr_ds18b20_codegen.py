"""Syntax-level integrity tests for Zephyr DS18B20 code generation.

Verifies the Zephyr backend produces a complete app/ tree with a
ds18b20.c driver, that the emitted C contains the expected Zephyr
sensor API calls, and that the prj.conf enables the DS18B20 driver.
"""

from pathlib import Path
from textwrap import dedent

import pytest

from demol.transformations.m2t_zephyr import m2t_zephyr

SYNTHETIC_DS18B20_MODEL = dedent("""\
    DEVICE SyntheticDs18b20 WITH description="ds18b20 codegen test", author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE DS18B20[Temp];

    CONNECT Temp WITH
        POWER GND -- gnd, VCC -- power_3v3
        DATA gpio data -- d3
        @ "test.ds18b20";
    """)


def test_ds18b20_app_tree_is_emitted(device_mm, tmp_path):
    """Generating a DS18B20 model produces the expected Zephyr app tree."""
    model = device_mm.model_from_str(SYNTHETIC_DS18B20_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    app_dir = tmp_path / "app"
    assert app_dir.is_dir(), "Missing app/ directory"

    assert (app_dir / "CMakeLists.txt").is_file(), "Missing CMakeLists.txt"
    assert (app_dir / "prj.conf").is_file(), "Missing prj.conf"
    assert (app_dir / "src" / "main.c").is_file(), "Missing src/main.c"
    assert (app_dir / "src" / "ds18b20.c").is_file(), "Missing src/ds18b20.c"

    overlays = list((app_dir / "boards").glob("*.overlay"))
    assert overlays, "Missing board overlay"


def test_ds18b20_driver_uses_zephyr_sensor_api(device_mm, tmp_path):
    """The generated ds18b20.c contains Zephyr sensor API calls."""
    model = device_mm.model_from_str(SYNTHETIC_DS18B20_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    ds18b20_c = tmp_path / "app" / "src" / "ds18b20.c"
    assert ds18b20_c.is_file()

    body = ds18b20_c.read_text(encoding="utf-8")
    assert "sensor_sample_fetch" in body, "Missing sensor_sample_fetch"
    assert "DEVICE_DT_GET" in body, "Missing DEVICE_DT_GET"
    assert "maxim_ds18b20" in body, "Missing maxim_ds18b20 compatible"
    assert "sensor_channel_get" in body, "Missing sensor_channel_get"
    assert "sensor_value_to_double" in body, "Missing sensor_value_to_double"
    assert "struct ds18b20_data" in body, "Missing ds18b20_data struct"
    assert "SENSOR_CHAN_AMBIENT_TEMP" in body, "Missing SENSOR_CHAN_AMBIENT_TEMP"


def test_ds18b20_prj_conf_has_kconfig(device_mm, tmp_path):
    """The generated prj.conf enables CONFIG_DS18B20."""
    model = device_mm.model_from_str(SYNTHETIC_DS18B20_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    prj_conf = (tmp_path / "app" / "prj.conf").read_text(encoding="utf-8")
    assert "CONFIG_DS18B20=y" in prj_conf, "Missing CONFIG_DS18B20 in prj.conf"


def test_ds18b20_cmakelists_lists_source(device_mm, tmp_path):
    """The generated CMakeLists.txt includes ds18b20.c in target_sources."""
    model = device_mm.model_from_str(SYNTHETIC_DS18B20_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    cmake = (tmp_path / "app" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "ds18b20.c" in cmake, "Missing ds18b20.c in CMakeLists.txt target_sources"
