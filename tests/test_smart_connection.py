"""Tests for the SmartConnect feature."""

import pytest
from textx.exceptions import TextXSemanticError

# ============================================================================
# Helper: base model template
# ============================================================================

BASE_MODEL = """
DEVICE {name} WITH description="test", author="test", os=raspbian;
USE RaspberryPi_5_8GB;
{uses}
NETWORK[WiFi] WITH ssid="t", password="t";
BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
{body}
"""


def make_model(uses, body, name="TestDevice"):
    return BASE_MODEL.format(name=name, uses=uses, body=body)


# ============================================================================
# Parsing tests
# ============================================================================


def test_smartconnect_basic_parse(device_mm):
    model = device_mm.model_from_str(make_model("USE HCSR04[Dist];", 'SMARTCONNECT Dist @ "sensors/dist";'))
    assert len(model.smartConnections) == 1
    assert model.smartConnections[0].target.name == "Dist"
    assert model.smartConnections[0].remote == "sensors/dist"
    assert len(model.connections) >= 1


def test_smartconnect_no_topic(device_mm):
    model = device_mm.model_from_str(make_model("USE BME680[Env];", "SMARTCONNECT Env;"))
    assert len(model.smartConnections) == 1
    conn = [c for c in model.connections if getattr(c, "_is_smart_connection", False)][0]
    assert conn.remote is not None and conn.remote != ""


def test_smartconnect_multiple(device_mm):
    model = device_mm.model_from_str(
        make_model(
            "USE BME680[Env], HCSR04[Dist];",
            'SMARTCONNECT Env @ "sensors/env";\nSMARTCONNECT Dist @ "sensors/dist";',
        )
    )
    assert len(model.smartConnections) == 2
    assert len(model.connections) == 2


# ============================================================================
# GPIO resolution tests
# ============================================================================


def test_smartconnect_gpio_sensor(device_mm):
    model = device_mm.model_from_str(make_model("USE HCSR04[Dist];", 'SMARTCONNECT Dist @ "sensors/dist";'))
    conn = model.connections[0]
    assert getattr(conn, "_is_smart_connection", False)

    # HCSR04 has 2 power pins (GND, 5V) and 2 GPIO pins (echo, trigger)
    assert len(conn.powerConns) == 2
    power_from = {pc.fromPin for pc in conn.powerConns}
    assert "GND" in power_from
    assert "VCC" in power_from

    gpio_conns = [dc for dc in conn.dataConns if dc.type == "gpio"]
    assert len(gpio_conns) == 2

    gpio_by_pin = {dc.pins[0].fromPin: dc for dc in gpio_conns}
    assert "echo" in gpio_by_pin
    assert "trigger" in gpio_by_pin

    # Per-pin modes from gpio_modes attribute: echo=input, trigger=output
    echo_mode = [p.value for p in gpio_by_pin["echo"].props if p.name == "mode"][0]
    trigger_mode = [p.value for p in gpio_by_pin["trigger"].props if p.name == "mode"][0]
    assert echo_mode == "input"
    assert trigger_mode == "output"


def test_smartconnect_gpio_actuator(device_mm):
    model = device_mm.model_from_str(make_model("USE BuzzerGeneric[Buzz];", 'SMARTCONNECT Buzz @ "actuators/buzz";'))
    conn = model.connections[0]
    gpio_conns = [dc for dc in conn.dataConns if dc.type == "gpio"]
    assert len(gpio_conns) >= 1

    for dc in gpio_conns:
        mode_props = [p for p in dc.props if p.name == "mode"]
        assert len(mode_props) == 1
        assert mode_props[0].value == "output"


def test_smartconnect_ws281x_as_gpio(device_mm):
    """WS281X data_in pin resolves as GPIO (not SPI) with mode=output."""
    model = device_mm.model_from_str(make_model("USE WS281X[Led];", 'SMARTCONNECT Led @ "actuators/led";'))
    conn = model.connections[0]
    gpio_conns = [dc for dc in conn.dataConns if dc.type == "gpio"]
    # WS281X has data_in + optional data_out
    assert len(gpio_conns) == 2
    assert gpio_conns[0].pins[0].fromPin == "data_in"

    mode = [p.value for p in gpio_conns[0].props if p.name == "mode"][0]
    assert mode == "output"

    spi_conns = [dc for dc in conn.dataConns if dc.type == "spi"]
    assert len(spi_conns) == 0


# ============================================================================
# I2C resolution tests
# ============================================================================


def test_smartconnect_i2c_sensor(device_mm):
    model = device_mm.model_from_str(make_model("USE BME680[Env];", 'SMARTCONNECT Env @ "sensors/env";'))
    conn = model.connections[0]

    # BME680: 2 power (vcc 5V, gnd GND), 2 I2C data (sda, scl)
    assert len(conn.powerConns) == 2

    i2c_conns = [dc for dc in conn.dataConns if dc.type == "i2c"]
    assert len(i2c_conns) == 1

    i2c = i2c_conns[0]
    assert len(i2c.pins) == 2

    pin_functions = {pm.function for pm in i2c.pins}
    assert "sda" in pin_functions
    assert "scl" in pin_functions

    # Check slave_address prop
    addr_props = [p for p in i2c.props if p.name == "slave_address"]
    assert len(addr_props) == 1
    assert addr_props[0].value == "0x76"


def test_smartconnect_i2c_sharing(device_mm):
    """Two I2C peripherals share SDA/SCL pins on same bus."""
    model = device_mm.model_from_str(
        make_model(
            "USE BME680[Env], VL53L1X[Dist];",
            'SMARTCONNECT Env @ "sensors/env";\nSMARTCONNECT Dist @ "sensors/dist";',
        )
    )
    assert len(model.connections) == 2

    # Both should use the same SDA/SCL board pins (I2C bus sharing)
    i2c_board_pins = []
    for conn in model.connections:
        for dc in conn.dataConns:
            if dc.type == "i2c":
                for pm in dc.pins:
                    i2c_board_pins.append(pm.toPin)

    sda_pins = [p for i, p in enumerate(i2c_board_pins) if i % 2 == 0]
    scl_pins = [p for i, p in enumerate(i2c_board_pins) if i % 2 == 1]

    # Both SDA should map to same board pin (GPIO2 on RPi5)
    assert len(set(sda_pins)) == 1
    # Both SCL should map to same board pin (GPIO3 on RPi5)
    assert len(set(scl_pins)) == 1


def test_smartconnect_i2c_different_addresses(device_mm):
    """Two I2C peripherals have different slave addresses."""
    model = device_mm.model_from_str(
        make_model(
            "USE BME680[Env], VL53L1X[Dist];",
            'SMARTCONNECT Env @ "sensors/env";\nSMARTCONNECT Dist @ "sensors/dist";',
        )
    )

    addresses = []
    for conn in model.connections:
        for dc in conn.dataConns:
            if dc.type == "i2c":
                for p in dc.props:
                    if p.name == "slave_address":
                        addresses.append(p.value)

    assert len(addresses) == 2
    assert addresses[0] != addresses[1]


# ============================================================================
# Mixed protocol tests
# ============================================================================


def test_smartconnect_mixed_manual_and_smart(device_mm):
    model = device_mm.model_from_str(
        make_model(
            "USE BME680[Env], HCSR04[Dist];",
            """
            CONNECT Env WITH
                POWER gnd -- GND_1, vcc -- power_5v_a
                DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
                @ "sensors/env";
            SMARTCONNECT Dist @ "sensors/dist";
            """,
        )
    )

    assert len(model.connections) == 2

    manual_conns = [c for c in model.connections if not getattr(c, "_is_smart_connection", False)]
    smart_conns = [c for c in model.connections if getattr(c, "_is_smart_connection", False)]

    assert len(manual_conns) == 1
    assert len(smart_conns) == 1

    # SmartConnect should avoid GPIO2, GPIO3 (used by manual I2C)
    smart = smart_conns[0]
    smart_board_pins = set()
    for dc in smart.dataConns:
        for pm in dc.pins:
            smart_board_pins.add(pm.toPin)

    assert "GPIO2" not in smart_board_pins
    assert "GPIO3" not in smart_board_pins


# ============================================================================
# Pin conflict avoidance tests
# ============================================================================


def test_smartconnect_avoids_manual_pins(device_mm):
    """SmartConnect doesn't use pins already claimed by manual CONNECT."""
    model = device_mm.model_from_str(
        make_model(
            "USE HCSR04[Dist1], HCSR04[Dist2];",
            """
            CONNECT Dist1 WITH
                POWER GND -- GND_1, VCC -- power_5v_a
                DATA gpio[mode="input"] echo -- GPIO4, gpio[mode="output"] trigger -- GPIO17
                @ "sensors/dist1";
            SMARTCONNECT Dist2 @ "sensors/dist2";
            """,
        )
    )

    smart = [c for c in model.connections if getattr(c, "_is_smart_connection", False)][0]
    smart_board_pins = set()
    for dc in smart.dataConns:
        for pm in dc.pins:
            smart_board_pins.add(pm.toPin)

    assert "GPIO4" not in smart_board_pins
    assert "GPIO17" not in smart_board_pins


# ============================================================================
# Optional pin tests
# ============================================================================


def test_smartconnect_optional_pins_connected_when_available(device_mm):
    """Optional pins ARE connected when board pins are available."""
    # VL53L1X has optional XSHUT[gpio] and GPIO1[gpio] pins
    model = device_mm.model_from_str(
        make_model(
            "USE VL53L1X[Dist];",
            'SMARTCONNECT Dist @ "sensors/dist";',
        )
    )
    conn = model.connections[0]

    # VL53L1X has: VIN[3V3], GND, SDA, SCL, ?VDD[2.8V], ?XSHUT[gpio], ?GPIO1[gpio]
    # VDD is 2.8V — RPi5 doesn't have a 2.8V power pin, so it should be skipped
    # XSHUT and GPIO1 are optional GPIO pins — should be connected if GPIOs available

    gpio_conns = [dc for dc in conn.dataConns if dc.type == "gpio"]
    gpio_periph_pins = {dc.pins[0].fromPin for dc in gpio_conns}

    # Optional GPIO pins should be connected (board has plenty of GPIO pins)
    assert "XSHUT" in gpio_periph_pins
    assert "GPIO1" in gpio_periph_pins


# ============================================================================
# Error tests
# ============================================================================


def test_smartconnect_duplicate_error(device_mm):
    with pytest.raises(TextXSemanticError, match="Duplicate SMARTCONNECT"):
        device_mm.model_from_str(
            make_model(
                "USE HCSR04[Dist];",
                'SMARTCONNECT Dist @ "sensors/dist";\nSMARTCONNECT Dist @ "sensors/dist2";',
            )
        )


def test_smartconnect_conflict_with_manual(device_mm):
    with pytest.raises(TextXSemanticError, match="already has a manual CONNECT"):
        device_mm.model_from_str(
            make_model(
                "USE HCSR04[Dist];",
                """
                CONNECT Dist WITH
                    POWER GND -- GND_1, VCC -- power_5v_a
                    DATA gpio[mode="input"] echo -- GPIO4, gpio[mode="output"] trigger -- GPIO17
                    @ "sensors/dist";
                SMARTCONNECT Dist @ "sensors/dist2";
                """,
            )
        )


# ============================================================================
# Enrichment tests
# ============================================================================


def test_smartconnect_enrichment_board(device_mm):
    """SmartConnect connections get board/peripheral attributes set by enrichment."""
    model = device_mm.model_from_str(make_model("USE BME680[Env];", 'SMARTCONNECT Env @ "sensors/env";'))
    conn = model.connections[0]

    assert hasattr(conn, "board") and conn.board is not None
    assert conn.board.name == "RaspberryPi_5_8GB"

    assert hasattr(conn, "peripheral") and conn.peripheral is not None
    assert conn.peripheral.name == "Env"


def test_smartconnect_enrichment_refs(device_mm):
    """SmartConnect connections get _from_ref/_to_ref set."""
    model = device_mm.model_from_str(make_model("USE BME680[Env];", 'SMARTCONNECT Env @ "sensors/env";'))
    conn = model.connections[0]

    assert hasattr(conn, "_from_ref")
    assert hasattr(conn, "_to_ref")


def test_smartconnect_topic_auto_generated(device_mm):
    """Topic is auto-generated when @ is omitted."""
    model = device_mm.model_from_str(make_model("USE BME680[Env];", "SMARTCONNECT Env;"))
    conn = [c for c in model.connections if getattr(c, "_is_smart_connection", False)][0]
    assert conn.remote is not None
    assert len(conn.remote) > 0


# ============================================================================
# Determinism tests
# ============================================================================


def test_smartconnect_deterministic_allocation(device_mm):
    """Same model always produces the same pin allocation."""
    model_str = make_model(
        "USE HCSR04[Dist];",
        'SMARTCONNECT Dist @ "sensors/dist";',
    )

    results = []
    for _ in range(3):
        model = device_mm.model_from_str(model_str)
        conn = model.connections[0]
        pins = []
        for dc in conn.dataConns:
            for pm in dc.pins:
                pins.append((pm.fromPin, pm.toPin))
        results.append(tuple(pins))

    assert results[0] == results[1] == results[2]


# ============================================================================
# No-connections model test
# ============================================================================


def test_smartconnect_only_model(device_mm):
    """Model with only SMARTCONNECT (no manual CONNECT) works."""
    model = device_mm.model_from_str(make_model("USE BME680[Env];", 'SMARTCONNECT Env @ "sensors/env";'))
    manual = [c for c in model.connections if not getattr(c, "_is_smart_connection", False)]
    smart = [c for c in model.connections if getattr(c, "_is_smart_connection", False)]

    assert len(manual) == 0
    assert len(smart) == 1


def test_spec_i2c_int_address_converted_to_hex(device_mm):
    model = device_mm.model_from_str(make_model("USE BME680[Env];", 'SMARTCONNECT Env @ "sensors/env";'))
    conn = model.connections[0]
    i2c_dcs = [dc for dc in conn.dataConns if dc.type == "i2c"]
    assert len(i2c_dcs) == 1
    addr_props = [p for p in i2c_dcs[0].props if p.name == "slave_address"]
    assert len(addr_props) == 1
    assert isinstance(addr_props[0].value, str)
    assert addr_props[0].value.startswith("0x")


def test_spec_spi_emits_single_dc_with_no_props(device_mm):
    model = device_mm.model_from_str(make_model("USE MFRC522[Rfid];", 'SMARTCONNECT Rfid @ "sensors/rfid";'))
    conn = model.connections[0]
    spi_dcs = [dc for dc in conn.dataConns if dc.type == "spi"]
    assert len(spi_dcs) == 1
    assert spi_dcs[0].props == []


def test_spec_pwm_emits_one_dc_per_pin(device_mm):
    model = device_mm.model_from_str(make_model("USE LedGeneric[Led];", 'SMARTCONNECT Led @ "actuators/led";'))
    conn = model.connections[0]
    pwm_dcs = [dc for dc in conn.dataConns if dc.type == "pwm"]
    assert len(pwm_dcs) >= 1
    for dc in pwm_dcs:
        assert len(dc.pins) == 1
        assert dc.props == []


def test_spec_gpio_sensor_infers_input_mode(device_mm):
    model = device_mm.model_from_str(make_model("USE HCSR04[Dist];", 'SMARTCONNECT Dist @ "sensors/dist";'))
    conn = model.connections[0]
    gpio_dcs = [dc for dc in conn.dataConns if dc.type == "gpio"]
    assert len(gpio_dcs) >= 1
    for dc in gpio_dcs:
        mode_props = [p for p in dc.props if p.name == "mode"]
        assert len(mode_props) == 1
        assert mode_props[0].value in ("input", "output")


def test_spec_dispatcher_uses_spec_name_for_dc_type():
    from demol.lang.smart_connection import _PWM_SPEC, _resolve_pins_with_spec
    from types import SimpleNamespace

    pin = SimpleNamespace(name="din", optional=None, funcs=[SimpleNamespace(ptype="pwm", channel=0)])
    peripheral_inst = SimpleNamespace(name="X", ref=None)
    sc = SimpleNamespace(name="sc")
    data_conns = []

    fake_board_pin = SimpleNamespace(name="GPIO18", number=18)
    pool = SimpleNamespace()
    pool.find_pwm_pin = lambda channel=None: fake_board_pin
    pool.mark_used = lambda *a, **k: None

    _resolve_pins_with_spec(_PWM_SPEC, [(pin, pin.funcs[0])], peripheral_inst, None, pool, sc, data_conns)
    assert len(data_conns) == 1
    assert data_conns[0].type == "pwm"
