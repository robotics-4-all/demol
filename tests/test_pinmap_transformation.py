"""Coverage tests for demol.transformations.m2t_pinmap.

The pinmap generator (10% baseline coverage) is exercised end-to-end:
helpers, the structured connection builder, the Markdown formatter, the
JSON serializer, and the public `generate_pinmap` entry point.
"""

import json
import os
from types import SimpleNamespace

import pytest

from demol.lang.device import get_device_mm
from demol.transformations.m2t_pinmap import (
    _build_connection_data,
    _extract_props,
    _format_props,
    _generate_json,
    _generate_markdown,
    _get_board_and_periph_pin,
    _get_pin_number,
    _get_power_type,
    _is_from_board,
    generate_pinmap,
)


def _build_model(demol_str: str):
    mm = get_device_mm()
    mm.skip_semantics = True
    return mm.model_from_str(demol_str)


def _find_conn(model, peripheral_name: str):
    for c in model.connections:
        if c.peripheral and c.peripheral.name == peripheral_name:
            return c
    raise AssertionError(f"no connection for {peripheral_name}")


# ── Helpers (low-level) ─────────────────────────────────────────────────────


def test_is_from_board_true_when_from_ref_matches_board():
    board = object()
    conn = SimpleNamespace(_from_ref=board)
    assert _is_from_board(conn, board) is True


def test_is_from_board_false_when_from_ref_is_other():
    conn = SimpleNamespace(_from_ref=object())
    assert _is_from_board(conn, object()) is False


def test_is_from_board_false_when_from_ref_missing():
    conn = SimpleNamespace()
    assert _is_from_board(conn, object()) is False


def test_get_board_and_periph_pin_when_from_is_board():
    board = object()
    pin_map = SimpleNamespace(fromPin="GPIO2", toPin="sda")
    conn = SimpleNamespace(_from_ref=board)
    b, p = _get_board_and_periph_pin(conn, pin_map, board)
    assert b == "GPIO2" and p == "sda"


def test_get_board_and_periph_pin_when_to_is_board():
    board = object()
    pin_map = SimpleNamespace(fromPin="sda", toPin="GPIO2")
    conn = SimpleNamespace(_from_ref=object())
    b, p = _get_board_and_periph_pin(conn, pin_map, board)
    assert b == "GPIO2" and p == "sda"


def test_get_pin_number_with_numbered_pin():
    pin = SimpleNamespace(number=7)
    assert _get_pin_number({"GPIO2": pin}, "GPIO2") == 7


def test_get_pin_number_returns_minus_one_for_missing_pin():
    assert _get_pin_number({}, "GPIO2") == -1


def test_get_pin_number_returns_minus_one_for_pin_without_number():
    pin = SimpleNamespace(spec=[])  # no .number attribute
    assert _get_pin_number({"GPIO2": pin}, "GPIO2") == -1


def test_get_power_type_returns_ptype_string():
    pin = SimpleNamespace(ptype="3V3")
    assert _get_power_type({"VCC_3V3": pin}, "VCC_3V3") == "3V3"


def test_get_power_type_returns_empty_for_missing_pin():
    assert _get_power_type({}, "VCC_3V3") == ""


def test_get_power_type_returns_empty_for_pin_without_ptype():
    pin = SimpleNamespace()
    assert _get_power_type({"VCC_3V3": pin}, "VCC_3V3") == ""


def test_extract_props_string_value():
    dc = SimpleNamespace(props=[SimpleNamespace(name="mode", value="output")])
    assert _extract_props(dc) == {"mode": "output"}


def test_extract_props_hex_string_preserved_as_string():
    dc = SimpleNamespace(props=[SimpleNamespace(name="slave_address", value="0x76")])
    assert _extract_props(dc) == {"slave_address": "0x76"}


def test_extract_props_int_value():
    dc = SimpleNamespace(props=[SimpleNamespace(name="baudrate", value=115200)])
    assert _extract_props(dc) == {"baudrate": 115200}


def test_format_props_empty_returns_empty_string():
    assert _format_props({}) == ""


def test_format_props_string_value_quoted():
    assert _format_props({"mode": "output"}) == 'mode="output"'


def test_format_props_non_string_value_unquoted():
    assert _format_props({"baudrate": 9600}) == "baudrate=9600"


def test_format_props_mixed_values():
    out = _format_props({"mode": "output", "baudrate": 9600})
    assert 'mode="output"' in out
    assert "baudrate=9600" in out
    assert ", " in out


# ── Structured builder ───────────────────────────────────────────────────────


def test_build_connection_data_power_only():
    model = _build_model("""
        DEVICE PinTest WITH description="x", author="t", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH
            POWER gnd -- GND_1, vcc -- power_5v_a;
        """)
    data = _build_connection_data(model)
    assert len(data) == 1
    entry = data[0]
    assert entry["peripheral"] == "EnvSensor"
    assert entry["peripheral_type"] == "BME680"
    assert entry["source"] == "manual"
    assert entry["topic"] == ""
    assert len(entry["power"]) == 2
    assert entry["data"] == []


def test_build_connection_data_i2c_data():
    model = _build_model("""
        DEVICE I2CTest WITH description="x", author="t", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH
            POWER gnd -- GND_1, vcc -- power_5v_a
            DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3
            @ "dev.sensor.env";
        """)
    data = _build_connection_data(model)
    assert len(data) == 1
    entry = data[0]
    assert entry["topic"] == "dev.sensor.env"
    assert len(entry["data"]) == 2
    for d in entry["data"]:
        assert d["protocol"].lower() == "i2c"
        assert "slave_address" in d["properties"]


def test_build_connection_data_smartconnect_flag():
    """Connections that the smart_connection resolver adds are flagged."""
    model = _build_model("""
        DEVICE SmartTest WITH description="x", author="t", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH
            POWER gnd -- GND_1, vcc -- power_5v_a;
        """)
    # Mark the first connection as smart
    model.connections[0]._is_smart_connection = True
    data = _build_connection_data(model)
    assert data[0]["source"] == "smartconnect"


def test_build_connection_data_missing_peripheral_attr_skipped():
    """A connection without a `.peripheral` attribute is skipped, not crashed."""
    model = _build_model("""
        DEVICE SkipTest WITH description="x", author="t", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH
            POWER gnd -- GND_1, vcc -- power_5v_a;
        """)
    conn = model.connections[0]
    # Simulate a connection with no `peripheral` attribute
    if hasattr(conn, "peripheral"):
        delattr(conn, "peripheral")
    data = _build_connection_data(model)
    assert data == []


# ── Markdown formatter ───────────────────────────────────────────────────────


def test_generate_markdown_basic_shape():
    model = _build_model("""
        DEVICE MdTest WITH description="x", author="alice", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH
            POWER gnd -- GND_1, vcc -- power_5v_a
            DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3
            @ "dev.sensor.env";
        """)
    connections = _build_connection_data(model)
    md = _generate_markdown(model, connections)

    assert md.startswith("# Pin Mapping: MdTest")
    assert "**Board:** RaspberryPi_5_8GB" in md
    assert "**Author:** alice" in md
    assert "**Connections:** 1" in md
    assert "## EnvSensor (BME680)" in md
    assert "### Power" in md
    assert "### Data" in md
    assert "`dev.sensor.env`" in md
    assert "## Summary" in md
    assert "| Peripherals | 1 |" in md
    assert "| Power connections | 2 |" in md
    assert "| Data connections | 2 |" in md
    assert "I2C" in md
    assert "slave_address" in md


def test_generate_markdown_no_author_omits_line():
    model = _build_model("""
        DEVICE NoAuth WITH description="x", author="x", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH POWER gnd -- GND_1, vcc -- power_5v_a;
        """)
    if hasattr(model.metadata, "author"):
        delattr(model.metadata, "author")
    connections = _build_connection_data(model)
    md = _generate_markdown(model, connections)
    assert "**Author:**" not in md


def test_generate_markdown_smartconnect_badge():
    model = _build_model("""
        DEVICE SmartBadge WITH description="x", author="t", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH POWER gnd -- GND_1, vcc -- power_5v_a;
        """)
    model.connections[0]._is_smart_connection = True
    connections = _build_connection_data(model)
    md = _generate_markdown(model, connections)
    assert "SmartConnect" in md
    assert "| SmartConnect resolved | 1 |" in md
    assert "| Manual connections | 0 |" in md


def test_generate_markdown_data_with_no_pin_number():
    model = _build_model("""
        DEVICE NoPinNum WITH description="x", author="t", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH
            POWER gnd -- GND_1, vcc -- power_5v_a
            DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3;
        """)
    # Drop the pin number on one of the board pins to exercise "?" fallback
    board = model.components.board
    for pin in board.pins:
        if pin.name == "GPIO2":
            del pin.number
    connections = _build_connection_data(model)
    md = _generate_markdown(model, connections)
    assert "| ? |" in md


# ── JSON serializer ─────────────────────────────────────────────────────────


def test_generate_json_shape():
    model = _build_model("""
        DEVICE JsonTest WITH description="x", author="bob", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH POWER gnd -- GND_1, vcc -- power_5v_a;
        """)
    connections = _build_connection_data(model)
    j = _generate_json(model, connections)
    assert j["device"] == "JsonTest"
    assert j["board"] == "RaspberryPi_5_8GB"
    assert j["author"] == "bob"
    assert len(j["connections"]) == 1


def test_generate_json_no_author_returns_empty_string():
    model = _build_model("""
        DEVICE NoAuthJson WITH description="x", author="x", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH POWER gnd -- GND_1, vcc -- power_5v_a;
        """)
    if hasattr(model.metadata, "author"):
        delattr(model.metadata, "author")
    j = _generate_json(model, [])
    assert j["author"] == ""


# ── Public entry point ──────────────────────────────────────────────────────


def test_generate_pinmap_writes_markdown_and_json(tmp_path):
    model = _build_model("""
        DEVICE FullTest WITH description="x", author="t", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH
            POWER gnd -- GND_1, vcc -- power_5v_a
            DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3
            @ "dev.sensor.env";
        """)
    files = generate_pinmap(model, output_dir=str(tmp_path))
    assert len(files) == 2
    md_path = tmp_path / "FullTest_pinmap.md"
    json_path = tmp_path / "FullTest_pinmap.json"
    assert md_path.exists()
    assert json_path.exists()
    assert "FullTest" in md_path.read_text()
    parsed = json.loads(json_path.read_text())
    assert parsed["device"] == "FullTest"
    assert len(parsed["connections"]) == 1


def test_generate_pinmap_default_output_dir_creates_files_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    model = _build_model("""
        DEVICE CwdTest WITH description="x", author="t", os=riotos;
        USE RaspberryPi_5_8GB;
        USE BME680 [EnvSensor];
        CONNECT EnvSensor WITH POWER gnd -- GND_1, vcc -- power_5v_a;
        """)
    files = generate_pinmap(model)
    assert any(f.endswith("CwdTest_pinmap.md") for f in files)
    assert any(f.endswith("CwdTest_pinmap.json") for f in files)
    assert (tmp_path / "CwdTest_pinmap.md").exists()
    assert (tmp_path / "CwdTest_pinmap.json").exists()
