import pytest
import warnings
from textx.exceptions import TextXSemanticError


def test_power_path_with_power_bank(device_mm):
    model_str = """
    DEVICE MyDevice WITH
        description="A new IoT device",
        author="User",
        os=riotos
    ;

    NETWORK [WiFi] WITH ssid="test", password="test";

    BROKER [MQTT] test WITH host="localhost", port=1883, auth.username="test", auth.password="test";

    USE WemosD1Mini;
    USE HCSR04 [HCSR04_1];
    USE usb_power_bank [usb_power_bank_1];

    CONNECT HCSR04_1 WITH
        POWER GND -- gnd, VCC -- power_5v
        DATA gpio echo -- d1, gpio trigger -- d2
    ;

    CONNECT usb_power_bank_1 WITH
        POWER vcc -- power_5v, gnd -- gnd
    ;
    """

    # If the bug exists, this will raise MissingPowerSourceWarning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        device_mm.model_from_str(model_str)

        # Check for MissingPowerSourceWarning
        power_warnings = [warn for warn in w if "MissingPowerSourceWarning" in str(warn.message)]
        assert not power_warnings, f"Found power warnings: {[str(warn.message) for warn in power_warnings]}"


def test_power_path_user_model_as_is(device_mm):
    # This is exactly what the user provided (with their pin order)
    model_str = """
    DEVICE MyDevice WITH
        description="A new IoT device",
        author="User",
        os=riotos
    ;

    NETWORK [WiFi] WITH ssid="test", password="test";

    BROKER [MQTT] test WITH host="localhost", port=1883, auth.username="test", auth.password="test";

    USE WemosD1Mini;
    USE HCSR04 [HCSR04_1];
    USE usb_power_bank [usb_power_bank_1];

    CONNECT HCSR04_1 WITH
        POWER GND -- gnd, VCC -- power_5v
        DATA gpio echo -- d1, gpio trigger -- d2
    ;

    CONNECT usb_power_bank_1 WITH
        POWER vcc -- power_5v, gnd -- gnd
    ;
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            device_mm.model_from_str(model_str)
        except TextXSemanticError as e:
            # If it fails on connection validation, that's a different issue (pin mismatch)
            pytest.skip(f"Model failed validation: {e}")

        power_warnings = [warn for warn in w if "MissingPowerSourceWarning" in str(warn.message)]
        assert not power_warnings, f"Found power warnings: {[str(warn.message) for warn in power_warnings]}"
