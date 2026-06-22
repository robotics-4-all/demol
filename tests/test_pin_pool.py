"""Unit tests for the extracted PinPool module.

Covers:
- PinPool.__init__ (board pin indexing, sort order)
- mark_used / mark_used_from_connections
- is_available (sharing rules: POWER always, I2C shareable, others exclusive)
- find_power_pin (voltage matching, shareable fallback)
- find_io_pin_by_function (I2C bus matching, SPI, UART, GPIO)
- find_gpio_pin and find_pwm_pin
- The helper predicates: is_power_pin, is_io_pin, is_optional
- classify_peripheral_io_pins

These tests use synthetic ``SimpleNamespace`` boards to exercise PinPool
in isolation, so they do not depend on the metamodel or any example files.
"""

from types import SimpleNamespace

import pytest

from demol.lang.pin_pool import (
    I2C_FUNCTIONS,
    SPI_FUNCTIONS,
    UART_FUNCTIONS,
    PinPool,
    is_io_pin,
    is_power_pin,
)
from demol.lang.smart_connection import classify_peripheral_io_pins, is_optional

# ── Helpers ────────────────────────────────────────────────────────────────


def _pin(name, number, *, ptype=None, funcs=None, optional=None):
    attrs = {"name": name, "number": number}
    if ptype is not None:
        attrs["ptype"] = ptype
    if funcs is not None:
        attrs["funcs"] = funcs
    if optional is not None:
        attrs["optional"] = optional
    return SimpleNamespace(**attrs)


def _func(ptype, bus=None, channel=None):
    attrs = {"ptype": ptype}
    if bus is not None:
        attrs["bus"] = bus
    if channel is not None:
        attrs["channel"] = channel
    return SimpleNamespace(**attrs)


def _board(pins):
    return SimpleNamespace(pins=pins)


# ── Helper predicate tests ─────────────────────────────────────────────────


def test_is_power_pin_true_when_ptype_and_no_funcs():
    pin = _pin("GND", 6, ptype="GND")
    assert is_power_pin(pin) is True


def test_is_power_pin_false_when_io_pin():
    pin = _pin("GPIO2", 3, funcs=[_func("gpio")])
    assert is_power_pin(pin) is False


def test_is_io_pin_true_when_funcs_attribute():
    pin = _pin("GPIO2", 3, funcs=[_func("gpio")])
    assert is_io_pin(pin) is True


def test_is_io_pin_false_when_power_pin():
    pin = _pin("VCC", 1, ptype="VCC")
    assert is_io_pin(pin) is False


def test_is_optional_recognises_question_mark_prefix():
    pin = _pin("GPIO27", 13, funcs=[_func("gpio")], optional="?")
    assert is_optional(pin) is True


def test_is_optional_false_when_not_marked():
    pin = _pin("GPIO27", 13, funcs=[_func("gpio")])
    assert is_optional(pin) is False


# ── PinPool.__init__ ───────────────────────────────────────────────────────


def test_pinpool_init_indexes_pins_by_name_and_sorts():
    board = _board(
        [
            _pin("GPIO27", 13, funcs=[_func("gpio")]),
            _pin("VCC", 1, ptype="3V3"),
            _pin("GPIO2", 3, funcs=[_func("sda", bus=1), _func("gpio")]),
            _pin("GND", 6, ptype="GND"),
        ]
    )
    pool = PinPool(board)

    assert set(pool._all_pins.keys()) == {"GPIO27", "VCC", "GPIO2", "GND"}
    # IO pins sorted by number: GPIO2 (3), GPIO27 (13)
    assert [p.name for p in pool._io_pins_sorted] == ["GPIO2", "GPIO27"]
    # Power pins sorted by number: VCC (1), GND (6)
    assert [p.name for p in pool._power_pins_sorted] == ["VCC", "GND"]
    # Initial usage is empty
    assert pool._usage == {}


# ── mark_used / is_available / mark_used_from_connections ─────────────────


def test_mark_used_and_is_available_starts_true():
    board = _board([_pin("GPIO2", 3, funcs=[_func("gpio")])])
    pool = PinPool(board)

    assert pool.is_available("GPIO2", "GPIO") is True

    pool.mark_used("GPIO2", "Led", "GPIO")
    assert pool.is_available("GPIO2", "GPIO") is False


def test_is_available_power_always_shareable():
    board = _board([_pin("GND", 6, ptype="GND")])
    pool = PinPool(board)

    pool.mark_used("GND", "Sensor1", "POWER")
    # Another device requesting POWER on the same pin should still be allowed
    assert pool.is_available("GND", "POWER") is True
    # But not for IO
    assert pool.is_available("GND", "GPIO") is False


def test_is_available_i2c_sda_shareable():
    board = _board([_pin("GPIO2", 3, funcs=[_func("sda", bus=1), _func("gpio")])])
    pool = PinPool(board)

    pool.mark_used("GPIO2", "BME680", "I2C-SDA")
    # Second I2C-SDA request on same pin is fine (bus architecture)
    assert pool.is_available("GPIO2", "I2C-SDA") is True
    # But I2C-SCL is not (different signal)
    assert pool.is_available("GPIO2", "I2C-SCL") is False
    # And GPIO is exclusive
    assert pool.is_available("GPIO2", "GPIO") is False


def test_is_available_i2c_pin_can_host_power_too():
    board = _board([_pin("GPIO2", 3, funcs=[_func("sda", bus=1), _func("gpio")])])
    pool = PinPool(board)

    pool.mark_used("GPIO2", "BME680", "I2C-SDA")
    # A subsequent POWER request: existing usages are all I2C-SDA, not POWER,
    # so per the rules the answer is False. Power is *not* mixed with I2C.
    assert pool.is_available("GPIO2", "POWER") is False


def test_mark_used_from_connections_skips_smart_connection_synthetic():
    board = _board(
        [
            _pin("GND", 6, ptype="GND"),
            _pin("GPIO2", 3, funcs=[_func("gpio")]),
        ]
    )
    pool = PinPool(board)

    manual_conn = SimpleNamespace(
        _is_smart_connection=False,
        from_comp=SimpleNamespace(ref=SimpleNamespace(__class__=type("Board", (), {}))),
        to_comp=None,
        powerConns=[
            SimpleNamespace(fromPin="GND", toPin="GND_SENSOR"),
        ],
        dataConns=[
            SimpleNamespace(
                type="gpio",
                pins=[
                    SimpleNamespace(fromPin="GPIO2", toPin="SIG"),
                ],
            ),
        ],
    )
    synthetic_conn = SimpleNamespace(
        _is_smart_connection=True,
        from_comp=None,
        to_comp=None,
        powerConns=[],
        dataConns=[],
    )

    pool.mark_used_from_connections([manual_conn, synthetic_conn])

    # Manual GND pin is marked as POWER
    assert pool.is_available("GND", "POWER") is True  # shareable
    # Manual GPIO2 is marked as GPIO and is now exclusive
    assert pool.is_available("GPIO2", "GPIO") is False


# ── find_power_pin ─────────────────────────────────────────────────────────


def test_find_power_pin_voltage_match_returns_unused_first():
    board = _board(
        [
            _pin("GND", 6, ptype="GND"),
            _pin("3V3_A", 1, ptype="3V3"),
            _pin("3V3_B", 17, ptype="3V3"),
        ]
    )
    pool = PinPool(board)

    # No prior usage → should pick the first by pin number
    pin = pool.find_power_pin("3V3")
    assert pin is not None
    assert pin.name == "3V3_A"
    assert pin.number == 1


def test_find_power_pin_falls_back_to_used_shareable_pin():
    board = _board(
        [
            _pin("3V3_A", 1, ptype="3V3"),
            _pin("3V3_B", 17, ptype="3V3"),
        ]
    )
    pool = PinPool(board)

    pool.mark_used("3V3_A", "Sensor1", "POWER")
    # 3V3_A is used but shareable; 3V3_B is unused → prefer unused
    pin = pool.find_power_pin("3V3")
    assert pin is not None
    assert pin.name == "3V3_B"


def test_find_power_pin_returns_shareable_when_no_unused_available():
    board = _board([_pin("3V3_A", 1, ptype="3V3")])
    pool = PinPool(board)

    pool.mark_used("3V3_A", "Sensor1", "POWER")
    # 3V3_A is the only 3V3 pin; it's used but shareable
    pin = pool.find_power_pin("3V3")
    assert pin is not None
    assert pin.name == "3V3_A"


def test_find_power_pin_no_match_returns_none():
    board = _board([_pin("GND", 6, ptype="GND")])
    pool = PinPool(board)

    assert pool.find_power_pin("5V") is None


# ── find_io_pin_by_function ───────────────────────────────────────────────


def test_find_io_pin_by_function_matches_simple_function():
    board = _board(
        [
            _pin("GPIO4", 7, funcs=[_func("gpio"), _func("sda", bus=1)]),
        ]
    )
    pool = PinPool(board)

    pin = pool.find_io_pin_by_function("sda")
    assert pin is not None
    assert pin.name == "GPIO4"


def test_find_io_pin_by_function_respects_bus_filter():
    board = _board(
        [
            _pin("GPIO2", 3, funcs=[_func("sda", bus=1)]),
            _pin("GPIO4", 7, funcs=[_func("sda", bus=0)]),  # different bus
        ]
    )
    pool = PinPool(board)

    # bus=None → first match
    assert pool.find_io_pin_by_function("sda").name == "GPIO2"
    # bus=1 → still GPIO2
    assert pool.find_io_pin_by_function("sda", bus=1).name == "GPIO2"
    # bus=0 → GPIO4
    assert pool.find_io_pin_by_function("sda", bus=0).name == "GPIO4"


def test_find_io_pin_by_function_returns_none_when_all_bus_mismatch():
    board = _board([_pin("GPIO2", 3, funcs=[_func("sda", bus=1)])])
    pool = PinPool(board)

    assert pool.find_io_pin_by_function("sda", bus=99) is None


# ── find_gpio_pin and find_pwm_pin ─────────────────────────────────────────


def test_find_gpio_pin_returns_first_available():
    board = _board(
        [
            _pin("GPIO2", 3, funcs=[_func("sda", bus=1), _func("gpio")]),
            _pin("GPIO4", 7, funcs=[_func("gpio")]),
        ]
    )
    pool = PinPool(board)

    pin = pool.find_gpio_pin()
    assert pin is not None
    assert pin.name == "GPIO2"  # first by number


def test_find_gpio_pin_skips_exclusive_use():
    board = _board(
        [
            _pin("GPIO2", 3, funcs=[_func("sda", bus=1), _func("gpio")]),
            _pin("GPIO4", 7, funcs=[_func("gpio")]),
        ]
    )
    pool = PinPool(board)

    pool.mark_used("GPIO2", "BME680", "I2C-SDA")
    # GPIO2 is still I2C-shareable but exclusive for GPIO → skip to GPIO4
    pin = pool.find_gpio_pin()
    assert pin is not None
    assert pin.name == "GPIO4"


def test_find_pwm_pin_with_channel_filter():
    board = _board(
        [
            _pin("GPIO12", 32, funcs=[_func("pwm", channel=0)]),
            _pin("GPIO13", 33, funcs=[_func("pwm", channel=1)]),
        ]
    )
    pool = PinPool(board)

    # No channel filter → first PWM pin by number
    assert pool.find_pwm_pin().name == "GPIO12"
    # Channel filter
    assert pool.find_pwm_pin(channel=1).name == "GPIO13"
    # No pin on that channel
    assert pool.find_pwm_pin(channel=99) is None


# ── classify_peripheral_io_pins ────────────────────────────────────────────


def test_classify_peripheral_io_pins_groups_by_protocol():
    i2c_func = _func("sda", bus=1)
    spi_func = _func("mosi")
    uart_func = _func("tx")
    pwm_func = _func("pwm")
    gpio_func = _func("gpio")

    pins = [
        _pin("sda1", 0, funcs=[i2c_func]),
        _pin("mosi1", 1, funcs=[spi_func]),
        _pin("tx1", 2, funcs=[uart_func]),
        _pin("pwm1", 3, funcs=[pwm_func]),
        _pin("gpio1", 4, funcs=[gpio_func]),
    ]
    classified = classify_peripheral_io_pins(pins)

    assert len(classified["i2c"]) == 1
    assert len(classified["spi"]) == 1
    assert len(classified["uart"]) == 1
    assert len(classified["pwm"]) == 1
    assert len(classified["gpio"]) == 1
    # Each tuple is (pin, primary_func)
    assert classified["i2c"][0][0].name == "sda1"
    assert classified["spi"][0][0].name == "mosi1"


def test_classify_peripheral_io_pins_prefers_i2c_when_mixed():
    mixed = _pin("GPIO2", 3, funcs=[_func("sda", bus=1), _func("gpio")])
    classified = classify_peripheral_io_pins([mixed])
    assert len(classified["i2c"]) == 1
    assert classified["i2c"][0][0].name == "GPIO2"
    assert len(classified["gpio"]) == 0


# ── Protocol constant sanity checks (catch accidental re-binding) ─────────


def test_protocol_function_sets_have_expected_members():
    assert I2C_FUNCTIONS == {"sda", "scl"}
    assert SPI_FUNCTIONS == {"mosi", "miso", "sck", "cs"}
    assert UART_FUNCTIONS == {"tx", "rx"}
