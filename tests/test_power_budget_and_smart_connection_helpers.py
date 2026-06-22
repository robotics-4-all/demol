"""Coverage tests for power_budget + smart_connection.

The existing test files (test_power_budget.py, test_smart_connection.py)
cover the main validation paths. This file adds coverage for the
private helpers + the structured `analyze_power_budget` / `analyze_*`
entry points that the CLI depends on.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from demol.lang.device import get_device_mm
from demol.lang.semantics.validators.power_budget import (
    DEFAULT_BOARD_MAX_CURRENT_A,
    PowerBudgetValidator,
    _get_peripheral_supply_budget_mw,
    _parse_capacity_mah,
    _parse_power_mw,
    analyze_power_budget,
    validate_power_budget,
)
from demol.lang.smart_connection import (
    classify_peripheral_io_pins,
    get_peripheral_attribute,
    get_primary_protocol,
    infer_gpio_mode,
    is_io_pin,
    is_optional,
    is_power_pin,
)


def _build(demol_str):
    mm = get_device_mm()
    mm.skip_semantics = True
    return mm.model_from_str(demol_str)


# ── power_budget: helpers ────────────────────────────────────────────────────


def test_parse_power_mw_none_returns_none():
    assert _parse_power_mw(None) is None


def test_parse_power_mw_missing_value_or_unit_returns_none():
    assert _parse_power_mw(SimpleNamespace(value=None, unit="mw")) is None
    assert _parse_power_mw(SimpleNamespace(value=100, unit=None)) is None


def test_parse_power_mw_w_converts_to_mw():
    assert _parse_power_mw(SimpleNamespace(value=1.0, unit="W")) == 1000.0


def test_parse_power_mw_mw_passthrough():
    assert _parse_power_mw(SimpleNamespace(value=500, unit="mW")) == 500


def test_parse_power_mw_uw_converts_to_mw():
    assert _parse_power_mw(SimpleNamespace(value=2000, unit="uW")) == 2.0


def test_parse_power_mw_unknown_unit_returns_none():
    assert _parse_power_mw(SimpleNamespace(value=1, unit="kW")) is None


def test_parse_capacity_mah_mah_passthrough():
    op = SimpleNamespace(capacity=2000, capacity_unit="mAh", voltage=None)
    assert _parse_capacity_mah(op) == 2000


def test_parse_capacity_mah_ah_converts_to_mah():
    op = SimpleNamespace(capacity=2.0, capacity_unit="Ah", voltage=None)
    assert _parse_capacity_mah(op) == 2000


def test_parse_capacity_mah_wh_converts_via_voltage():
    op = SimpleNamespace(capacity=3.7, capacity_unit="Wh", voltage="3.7V")
    assert _parse_capacity_mah(op) == pytest.approx(1000.0, rel=1e-3)


def test_parse_capacity_mah_wh_no_voltage_returns_none():
    op = SimpleNamespace(capacity=3.7, capacity_unit="Wh", voltage=None)
    assert _parse_capacity_mah(op) is None


def test_parse_capacity_mah_unknown_unit_returns_none():
    op = SimpleNamespace(capacity=1, capacity_unit="kWh", voltage=None)
    assert _parse_capacity_mah(op) is None


def test_get_peripheral_supply_budget_no_vcc_returns_none():
    board = SimpleNamespace(operational=SimpleNamespace(vcc=None))
    assert _get_peripheral_supply_budget_mw(board) is None


def test_get_peripheral_supply_budget_no_op_returns_none():
    assert _get_peripheral_supply_budget_mw(SimpleNamespace()) is None


def test_get_peripheral_supply_budget_5v_with_avg():
    """5V rail default = 1.5A = 7500mW minus board own avg."""
    board = SimpleNamespace(
        operational=SimpleNamespace(
            vcc="5V",
            avg=SimpleNamespace(value=500, unit="mW"),
            max=None,
        )
    )
    result = _get_peripheral_supply_budget_mw(board)
    assert result == pytest.approx(7000.0, rel=1e-3)


def test_get_peripheral_supply_budget_3v3_default():
    """3.3V rail default = 0.5A = 1650mW."""
    board = SimpleNamespace(
        operational=SimpleNamespace(
            vcc="3V3",
            avg=None,
            max=None,
        )
    )
    result = _get_peripheral_supply_budget_mw(board)
    assert result == pytest.approx(1650.0, rel=1e-3)


def test_get_peripheral_supply_budget_12v_default():
    board = SimpleNamespace(
        operational=SimpleNamespace(
            vcc="12V",
            avg=None,
            max=None,
        )
    )
    result = _get_peripheral_supply_budget_mw(board)
    assert result == pytest.approx(24000.0, rel=1e-3)


def test_default_board_max_current_dict_has_common_voltages():
    for v in (3.3, 5.0, 12.0):
        assert v in DEFAULT_BOARD_MAX_CURRENT_A


# ── power_budget: public entry points ──────────────────────────────────────


def test_validate_power_budget_no_peripherals_returns_silently():
    model_str = """
    DEVICE NoPeriph WITH description="x", author="t", os=raspbian;
    USE RaspberryPi_5_8GB;
    NETWORK [WiFi] WITH ssid="s", password="p";
    BROKER [MQTT] MyBroker WITH host="localhost", port=1883;
    """
    model = _build(model_str)
    validate_power_budget(model)


def test_analyze_power_budget_returns_structured_dict():
    model_str = """
    DEVICE AnalyzeDev WITH description="x", author="t", os=raspbian;
    USE RaspberryPi_5_8GB;
    USE BME680 [E];
    NETWORK [WiFi] WITH ssid="s", password="p";
    BROKER [MQTT] MyBroker WITH host="localhost", port=1883;
    CONNECT E WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3;
    """
    model = _build(model_str)
    data = analyze_power_budget(model)
    assert "board" in data
    assert "peripherals" in data
    assert "totals" in data
    assert "budget" in data
    assert "power_sources" in data
    assert data["board"] is not None
    assert data["board"]["name"] == "RaspberryPi_5_8GB"
    assert data["totals"]["count"] >= 1


# ── smart_connection: helpers ─────────────────────────────────────────────


def test_is_power_pin_true_for_gnd():
    pin = SimpleNamespace(name="GND", ptype="GND")
    assert is_power_pin(pin) is True


def test_is_io_pin_true_for_io_with_funcs():
    pin = SimpleNamespace(name="GPIO2", funcs=[SimpleNamespace(ptype="gpio")])
    assert is_io_pin(pin) is True


def test_is_io_pin_false_for_power():
    pin = SimpleNamespace(name="GND", ptype="GND")
    assert is_io_pin(pin) is False


def test_is_optional_yes():
    pin = SimpleNamespace(optional="?")
    assert is_optional(pin) is True


def test_is_optional_no_when_attr_missing():
    pin = SimpleNamespace()
    assert is_optional(pin) is False


def test_is_optional_no_when_explicitly_empty():
    pin = SimpleNamespace(optional="")
    assert is_optional(pin) is False


def test_get_primary_protocol_i2c_wins():
    assert get_primary_protocol([SimpleNamespace(ptype="gpio")])[0].ptype == "gpio"
    assert get_primary_protocol([SimpleNamespace(ptype="i2c")])[0].ptype == "i2c"
    assert (
        get_primary_protocol(
            [
                SimpleNamespace(ptype="i2c"),
                SimpleNamespace(ptype="spi"),
            ]
        )[0].ptype
        == "i2c"
    )


def test_classify_peripheral_io_pins_returns_dict_with_expected_keys():
    pins = [
        SimpleNamespace(name="sda", funcs=[SimpleNamespace(ptype="sda-0")]),
        SimpleNamespace(name="scl", funcs=[SimpleNamespace(ptype="scl-0")]),
        SimpleNamespace(name="tx", funcs=[SimpleNamespace(ptype="tx-0")]),
    ]
    result = classify_peripheral_io_pins(pins)
    assert set(result.keys()) == {"i2c", "spi", "uart", "pwm", "gpio"}
    for category, pin_list in result.items():
        assert isinstance(pin_list, list)
    total = sum(len(v) for v in result.values())
    assert total == 3


def test_get_peripheral_attribute_returns_value():
    periph = SimpleNamespace(attributes=[SimpleNamespace(name="addr", default="0x76")])
    assert get_peripheral_attribute(periph, "addr") == "0x76"


def test_get_peripheral_attribute_missing_returns_none():
    periph = SimpleNamespace(attributes=[])
    assert get_peripheral_attribute(periph, "missing") is None


def test_infer_gpio_mode_actuator_returns_output():
    class FakeActuator:
        pass

    assert infer_gpio_mode(FakeActuator()) == "output"


def test_infer_gpio_mode_sensor_returns_input():
    class FakeSensor:
        pass

    assert infer_gpio_mode(FakeSensor()) == "input"
