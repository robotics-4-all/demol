import pytest
import warnings
from textx.exceptions import TextXSemanticError
from demol.lang.device import get_device_mm


@pytest.fixture
def device_mm():
    return get_device_mm()


def test_power_path_valid_board_to_peripheral(device_mm):
    """
    Test valid power path: Board is powered (implicitly or explicitly)
    and provides power to peripheral.
    """
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=riotos;
    NETWORK [WiFi] WITH ssid="test", password="test";
    BROKER [MQTT] test WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE HCSR04 [HCSR04_1];
    USE usb_power_bank [usb_power_bank_1];

    CONNECT usb_power_bank_1 WITH
        POWER vcc -- power_5v, gnd -- gnd
    ;

    CONNECT HCSR04_1 WITH
        POWER VCC -- power_5v, GND -- gnd
        DATA gpio echo -- d1, gpio trigger -- d2
    ;
    """
    # This should pass without MissingPowerSourceWarning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        # Check that no MissingPowerSourceWarning was raised
        power_warnings = [warning for warning in w if "MissingPowerSourceWarning" in str(warning.message)]
        assert len(power_warnings) == 0, f"Unexpected power warnings: {power_warnings}"


def test_power_path_valid_direct_powersource(device_mm):
    """
    Test valid power path: Peripheral powered directly by power source.
    """
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=riotos;
    NETWORK [WiFi] WITH ssid="test", password="test";
    BROKER [MQTT] test WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE HCSR04 [HCSR04_1];
    USE usb_power_bank [usb_power_bank_1];

    // Power source directly to peripheral
    CONNECT usb_power_bank_1 : HCSR04_1 WITH
        POWER vcc -- VCC, gnd -- GND
    ;

    CONNECT HCSR04_1 WITH
        DATA gpio echo -- d1, gpio trigger -- d2
    ;
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        power_warnings = [warning for warning in w if "MissingPowerSourceWarning" in str(warning.message)]
        # Board should have warning, but peripheral should not
        _board_warnings = [warning for warning in power_warnings if "WemosD1Mini" in str(warning.message)]
        periph_warnings = [warning for warning in power_warnings if "HCSR04_1" in str(warning.message)]
        assert len(periph_warnings) == 0, f"Peripheral should not have power warning: {periph_warnings}"


def test_power_path_missing_board_power(device_mm):
    """
    Test warning when board has no power source.
    """
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=riotos;
    NETWORK [WiFi] WITH ssid="test", password="test";
    BROKER [MQTT] test WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE HCSR04 [HCSR04_1];
    USE usb_power_bank [usb_power_bank_1];

    // Peripheral connected to board, but board has no power source
    CONNECT HCSR04_1 WITH
        POWER VCC -- power_5v, GND -- gnd
        DATA gpio echo -- d1, gpio trigger -- d2
    ;
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        power_warnings = [warning for warning in w if "MissingPowerSourceWarning" in str(warning.message)]
        # Both board and peripheral should have warnings
        assert len(power_warnings) >= 2, f"Expected warnings for board and peripheral: {power_warnings}"


def test_power_path_missing_peripheral_power(device_mm):
    """
    Test warning when peripheral has no power connection.
    """
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=riotos;
    NETWORK [WiFi] WITH ssid="test", password="test";
    BROKER [MQTT] test WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE HCSR04 [HCSR04_1];
    USE usb_power_bank [usb_power_bank_1];

    CONNECT usb_power_bank_1 WITH
        POWER vcc -- power_5v, gnd -- gnd
    ;

    CONNECT HCSR04_1 WITH
        // Missing POWER connection
        DATA gpio echo -- d1, gpio trigger -- d2
    ;
    """
    # This will fail with MissingEssentialConnectionError because VCC/GND are essential for HCSR04
    with pytest.raises(TextXSemanticError, match="Essential pin '(VCC|GND)'"):
        device_mm.model_from_str(model_str)


def test_power_path_chained_power(device_mm):
    """
    Test chained power: PowerSource -> Board -> Peripheral.
    """
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=riotos;
    NETWORK [WiFi] WITH ssid="test", password="test";
    BROKER [MQTT] test WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE HCSR04 [HCSR04_1];
    USE usb_power_bank [usb_power_bank_1];

    // Power source to board
    CONNECT usb_power_bank_1 WITH
        POWER vcc -- power_5v, gnd -- gnd
    ;

    // Board to peripheral
    CONNECT HCSR04_1 WITH
        POWER VCC -- power_5v, GND -- gnd
        DATA gpio echo -- d1, gpio trigger -- d2
    ;
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        power_warnings = [warning for warning in w if "MissingPowerSourceWarning" in str(warning.message)]
        assert len(power_warnings) == 0, f"No power warnings expected: {power_warnings}"


def test_power_path_gnd_only_not_enough(device_mm):
    """
    Test that GND-only connection does not satisfy power path requirement.
    """
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=riotos;
    NETWORK [WiFi] WITH ssid="test", password="test";
    BROKER [MQTT] test WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE HCSR04 [HCSR04_1];
    USE usb_power_bank [usb_power_bank_1];

    CONNECT usb_power_bank_1 WITH
        POWER gnd -- gnd // Only GND
    ;

    CONNECT HCSR04_1 WITH
        POWER VCC -- power_5v, GND -- gnd // Peripheral has VCC but Board doesn't have it from source
        DATA gpio echo -- d1, gpio trigger -- d2
    ;
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        power_warnings = [warning for warning in w if "MissingPowerSourceWarning" in str(warning.message)]
        # Should have warnings because GND-only is not sufficient
        assert len(power_warnings) > 0, "Expected power warnings for insufficient power connection"


def test_power_path_multiple_sources(device_mm):
    """
    Test multiple power sources.
    """
    model_str = """
    DEVICE MyDevice WITH description="Test", author="User", os=riotos;
    NETWORK [WiFi] WITH ssid="test", password="test";
    BROKER [MQTT] test WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE HCSR04 [HCSR04_1];
    USE usb_power_bank [usb_power_bank_1];
    USE li_ion_3v7 [battery_1];

    // Board powered by battery
    CONNECT battery_1 WITH
        POWER vcc -- power_3v3, gnd -- gnd
    ;

    // Peripheral powered by power bank
    CONNECT usb_power_bank_1 : HCSR04_1 WITH
        POWER vcc -- VCC, gnd -- GND
    ;

    CONNECT HCSR04_1 WITH
        DATA gpio echo -- d1, gpio trigger -- d2
    ;
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)
        power_warnings = [warning for warning in w if "MissingPowerSourceWarning" in str(warning.message)]
        # No warnings expected - both board and peripheral have power
        periph_warnings = [warning for warning in power_warnings if "HCSR04_1" in str(warning.message)]
        assert len(periph_warnings) == 0, f"Peripheral should not have power warning: {periph_warnings}"
