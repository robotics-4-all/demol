from textx.exceptions import TextXSemanticError
import pytest


def test_board_ports_validation_valid(component_mm):
    model_str = """
    BOARD[ESP] ValidBoard WITH
        OP
            vcc=3V3
        PORTS
            gpio=2
        PINS
            p1[gpio] @ 1,
            p2[gpio] @ 2
    ;
    """
    model = component_mm.model_from_str(model_str)
    assert model.component.name == "ValidBoard"


def test_board_ports_validation_invalid_gpio_count(component_mm):
    model_str = """
    BOARD[ESP] InvalidBoard WITH
        OP
            vcc=3V3
        PORTS
            gpio=3
        PINS
            p1[gpio] @ 1,
            p2[gpio] @ 2
    ;
    """
    with pytest.raises(TextXSemanticError, match="Declared 3 GPIO pins, but only found 2"):
        component_mm.model_from_str(model_str)


def test_board_ports_validation_invalid_spi_count(component_mm):
    model_str = """
    BOARD[ESP] InvalidSPIBoard WITH
        OP
            vcc=3V3
        PORTS
            spi=2
        PINS
            p1[gpio, mosi-0] @ 1,
            p2[gpio, miso-0] @ 2,
            p3[gpio, sck-0] @ 3
    ;
    """
    # Only bus 0 is defined, but we asked for 2 SPI interfaces
    with pytest.raises(TextXSemanticError, match="Declared 2 SPI interfaces, but only found pins for 1 buses"):
        component_mm.model_from_str(model_str)


def test_board_nested_properties(component_mm):
    model_str = """
    BOARD[ESP] PropBoard WITH
        OP
            vcc=3V3,
            wifi.name=MyWifi,
            wifi.bands=[2.4GHz, 5GHz],
            cpu.freq=240 mhz
        PINS
            p1[gpio] @ 1
    ;
    """
    model = component_mm.model_from_str(model_str)
    op = model.component.operational
    assert op.wifi_name == "MyWifi"
    assert "2.4GHz" in op.wifi_bands
    assert "5GHz" in op.wifi_bands
    assert op.cpu_freq == 240.0


def test_unique_pin_numbers(component_mm):
    model_str = """
    BOARD[ESP] DuplicatePinBoard WITH
        OP
            vcc=3V3
        PINS
            p1[gpio] @ 1,
            p2[gpio] @ 1
    ;
    """
    with pytest.raises(TextXSemanticError, match="Duplicate pin number"):
        component_mm.model_from_str(model_str)
