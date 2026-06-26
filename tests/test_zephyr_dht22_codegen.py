"""Syntax-level integrity tests for Zephyr DHT22 code generation.

Verifies the Zephyr backend produces a complete app/ tree with a
dht22.c GPIO bit-bang driver, that the emitted C contains the expected
Zephyr GPIO API calls, and that the prj.conf enables the DHT22 driver.
"""

from pathlib import Path
from textwrap import dedent

import pytest

from demol.transformations.m2t_zephyr import m2t_zephyr

SYNTHETIC_DHT22_MODEL = dedent("""\
    DEVICE SyntheticDht22 WITH description="dht22 codegen test", author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE DHT22[Env];

    CONNECT Env WITH
        POWER GND -- gnd, VCC -- power_3v3
        DATA gpio data -- d3
        @ "test.dht22";
    """)


def test_dht22_app_tree_is_emitted(device_mm, tmp_path):
    """Generating a DHT22 model produces the expected Zephyr app tree."""
    model = device_mm.model_from_str(SYNTHETIC_DHT22_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    app_dir = tmp_path / "app"
    assert app_dir.is_dir(), "Missing app/ directory"

    assert (app_dir / "CMakeLists.txt").is_file(), "Missing CMakeLists.txt"
    assert (app_dir / "prj.conf").is_file(), "Missing prj.conf"
    assert (app_dir / "src" / "main.c").is_file(), "Missing src/main.c"
    assert (app_dir / "src" / "dht22.c").is_file(), "Missing src/dht22.c"

    overlays = list((app_dir / "boards").glob("*.overlay"))
    assert overlays, "Missing board overlay"

    bindings = list((app_dir / "dts" / "bindings").glob("*.yaml"))
    assert bindings, "Missing devicetree binding YAMLs"


def test_dht22_driver_uses_zephyr_gpio_api(device_mm, tmp_path):
    """The generated dht22.c contains Zephyr GPIO API calls."""
    model = device_mm.model_from_str(SYNTHETIC_DHT22_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    dht22_c = tmp_path / "app" / "src" / "dht22.c"
    assert dht22_c.is_file()

    body = dht22_c.read_text(encoding="utf-8")
    assert "gpio_pin_configure_dt" in body, "Missing gpio_pin_configure_dt"
    assert "gpio_pin_get_dt" in body, "Missing gpio_pin_get_dt"
    assert "GPIO_DT_SPEC_GET" in body, "Missing GPIO_DT_SPEC_GET"
    assert "demol_dht22" in body, "Missing demol_dht22 compatible"
    assert "k_busy_wait" in body, "Missing k_busy_wait for timing"
    assert "struct dht22_data" in body, "Missing dht22_data struct"


def test_dht22_prj_conf_has_kconfig(device_mm, tmp_path):
    """The generated prj.conf enables CONFIG_DHT22."""
    model = device_mm.model_from_str(SYNTHETIC_DHT22_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    prj_conf = (tmp_path / "app" / "prj.conf").read_text(encoding="utf-8")
    assert "CONFIG_DHT22=y" in prj_conf, "Missing CONFIG_DHT22 in prj.conf"


def test_dht22_cmakelists_lists_source(device_mm, tmp_path):
    """The generated CMakeLists.txt includes dht22.c in target_sources."""
    model = device_mm.model_from_str(SYNTHETIC_DHT22_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    cmake = (tmp_path / "app" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "dht22.c" in cmake, "Missing dht22.c in CMakeLists.txt target_sources"


def test_dht22_gpio_overlay_node_emitted(device_mm, tmp_path):
    """The overlay contains a demol,dht22 node with data-gpios."""
    model = device_mm.model_from_str(SYNTHETIC_DHT22_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    overlays = list((tmp_path / "app" / "boards").glob("*.overlay"))
    assert overlays, "Missing board overlay"

    overlay = overlays[0].read_text(encoding="utf-8")
    assert "demol,dht22" in overlay, "Missing demol,dht22 compatible in overlay"
    assert "data-gpios" in overlay, "Missing data-gpios in overlay"
    assert 'status = "okay"' in overlay, "Missing status okay in overlay"


def test_dht22_binding_yaml_emitted(device_mm, tmp_path):
    """The dts/bindings directory contains a demol,dht22.yaml binding."""
    model = device_mm.model_from_str(SYNTHETIC_DHT22_MODEL)
    m2t_zephyr(model, output_dir=str(tmp_path))

    binding = tmp_path / "app" / "dts" / "bindings" / "demol-dht22.yaml"
    assert binding.is_file(), "Missing demol-dht22.yaml binding"

    body = binding.read_text(encoding="utf-8")
    assert 'compatible: "demol,dht22"' in body
    assert "data-gpios" in body
    assert "phandle-array" in body
