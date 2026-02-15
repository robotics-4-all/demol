"""
Parser Robustness & Fuzz Tests

Tests that verify the parser handles malformed, incomplete, and boundary-case
input gracefully — producing clear error messages rather than crashing or
exposing internal parser details.

Coverage areas:
 - Completely empty / whitespace-only input
 - Missing required keywords (DEVICE, USE, CONNECT, BROKER, etc.)
 - Malformed syntax (unclosed brackets, missing semicolons, bad operators)
 - Boundary values (extreme numbers, very long identifiers, special characters)
 - Incomplete blocks (truncated mid-parse)
 - Wrong keyword order
 - Duplicate / conflicting clauses
 - Unicode and encoding edge cases
"""

import pytest
from textx.exceptions import TextXSyntaxError, TextXSemanticError

# ===========================================================================
# Helpers
# ===========================================================================

VALID_PREAMBLE = """
DEVICE TestDevice WITH description="test", author="test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[Sensor1];
NETWORK[WiFi] WITH ssid="net", password="pass";
BROKER[MQTT] TestBroker WITH host="localhost", port=1883, auth.username="user", auth.password="pass";
CONNECT Sensor1 WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "test/topic";
"""


# ===========================================================================
# 1. Empty / Whitespace Input
# ===========================================================================


class TestEmptyInput:
    def test_completely_empty_input(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("")

    def test_whitespace_only(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("   \n\t\n   ")

    def test_comment_only(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("// This is just a comment\n")

    def test_block_comment_only(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("/* block comment */")


# ===========================================================================
# 2. Missing Required Keywords
# ===========================================================================


class TestMissingKeywords:
    def test_no_device_keyword(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            USE RaspberryPi_5_8GB;
            """)

    def test_device_without_with(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice description="x", author="y";
            """)

    def test_device_missing_description(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH author="test";
            """)

    def test_device_missing_author(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test";
            """)

    def test_device_missing_semicolon(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test"
            USE RaspberryPi_5_8GB;
            """)

    def test_use_missing_semicolon(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB
            """)


# ===========================================================================
# 3. Malformed Syntax
# ===========================================================================


class TestMalformedSyntax:
    def test_unclosed_bracket_in_network(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            NETWORK[WiFi WITH ssid="net", password="pass123";
            """)

    def test_unclosed_string(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="unclosed, author="test";
            """)

    def test_invalid_operator_in_constraint(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            CONSTRAINT bad: count(SENSOR) <> 1;
            """)

    def test_connect_without_with(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            USE BME680[Sensor1];
            CONNECT Sensor1
                POWER gnd -- GND_1;
            """)

    def test_data_with_unknown_protocol(self, device_mm):
        """Unknown protocol type should fail at parse or semantic level"""
        with pytest.raises((TextXSyntaxError, TextXSemanticError)):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            USE BME680[Sensor1];
            BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
            NETWORK[WiFi] WITH ssid="n", password="p";
            CONNECT Sensor1 WITH
                POWER gnd -- GND_1, vcc -- power_5v_a
                DATA canbus sda sda -- GPIO2
                @ "test/topic";
            """)

    def test_double_semicolons(self, device_mm):
        """Double semicolons should not crash the parser"""
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";;
            """)

    def test_missing_pin_separator(self, device_mm):
        """Pin connection without '--' separator"""
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            USE BME680[Sensor1];
            CONNECT Sensor1 WITH
                POWER GND_1 gnd;
            """)


# ===========================================================================
# 4. Boundary Values
# ===========================================================================


class TestBoundaryValues:
    def test_moderately_long_device_name(self, device_mm):
        """Parser should handle a moderately long identifier"""
        long_name = "A" * 50
        model_str = (
            f'DEVICE {long_name} WITH description="test", author="test";\n'
            "USE RaspberryPi_5_8GB;\n"
            "USE BME680[Sensor1];\n"
            'NETWORK[WiFi] WITH ssid="n", password="p";\n'
            'BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";\n'
            "CONNECT Sensor1 WITH\n"
            "    POWER gnd -- GND_1, vcc -- power_5v_a\n"
            "    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3\n"
            '    @ "test/topic";\n'
        )
        model = device_mm.model_from_str(model_str)
        assert model.metadata.name == long_name

    def test_zero_sampling_rate(self, device_mm):
        """Zero sampling rate should be caught by validator"""
        with pytest.raises((TextXSemanticError, TextXSyntaxError)):
            device_mm.model_from_str(VALID_PREAMBLE + """
            SAMPLING Sensor1 WITH rate = 0 hz;
            """)

    def test_negative_sampling_rate(self, device_mm):
        """Negative sampling rate"""
        with pytest.raises((TextXSemanticError, TextXSyntaxError)):
            device_mm.model_from_str(VALID_PREAMBLE + """
            SAMPLING Sensor1 WITH rate = -5 hz;
            """)

    def test_very_large_i2c_address(self, device_mm):
        """I2C address way above 0x7F should be caught"""
        with pytest.raises(TextXSemanticError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            USE BME680[Sensor1];
            NETWORK[WiFi] WITH ssid="n", password="p";
            BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
            CONNECT Sensor1 WITH
                POWER gnd -- GND_1, vcc -- power_5v_a
                DATA i2c[slave_address=0xFF] sda sda -- GPIO2, scl scl -- GPIO3
                @ "test/topic";
            """)

    def test_very_long_topic_string(self, device_mm):
        """Very long topic string should parse fine"""
        long_topic = "a/" * 200 + "end"
        model = device_mm.model_from_str(
            'DEVICE TestDevice WITH description="test", author="test";\n'
            "USE RaspberryPi_5_8GB;\n"
            "USE BME680[Sensor1];\n"
            'NETWORK[WiFi] WITH ssid="n", password="p";\n'
            'BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";\n'
            "CONNECT Sensor1 WITH\n"
            "    POWER gnd -- GND_1, vcc -- power_5v_a\n"
            "    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3\n"
            f'    @ "{long_topic}";\n'
        )
        assert long_topic in model.connections[0].remote

    def test_empty_string_description(self, device_mm):
        """Empty string for description should parse"""
        model = device_mm.model_from_str("""
        DEVICE TestDevice WITH description="", author="";
        USE RaspberryPi_5_8GB;
        USE BME680[Sensor1];
        NETWORK[WiFi] WITH ssid="n", password="p";
        BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
        CONNECT Sensor1 WITH
            POWER gnd -- GND_1, vcc -- power_5v_a
            DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
            @ "test/topic";
        """)
        assert model.metadata.description == ""


# ===========================================================================
# 5. Incomplete / Truncated Input
# ===========================================================================


class TestIncompleteInput:
    def test_truncated_after_device(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("DEVICE")

    def test_truncated_after_device_name(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("DEVICE TestDevice")

    def test_truncated_after_with(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("DEVICE TestDevice WITH")

    def test_truncated_connect_block(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            USE BME680(Sensor1);
            CONNECT Sensor1 WITH
                POWER GND_1 -- gnd
            """)

    def test_truncated_sampling(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            SAMPLING Sensor1 WITH rate =
            """)

    def test_truncated_alert(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            ALERT myalert ON Sensor1 WHEN
            """)

    def test_truncated_constraint(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            CONSTRAINT bad: count(SENSOR) >=
            """)


# ===========================================================================
# 6. Wrong Keyword Ordering
# ===========================================================================


class TestKeywordOrdering:
    def test_sampling_before_connect(self, device_mm):
        """SAMPLING before CONNECT should parse due to unordered group"""
        model = device_mm.model_from_str("""
        DEVICE TestDevice WITH description="test", author="test";
        USE RaspberryPi_5_8GB;
        USE BME680[Sensor1];
        NETWORK[WiFi] WITH ssid="n", password="p";
        BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
        SAMPLING Sensor1 WITH rate = 10 hz;
        CONNECT Sensor1 WITH
            POWER gnd -- GND_1, vcc -- power_5v_a
            DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
            @ "test/topic";
        """)
        assert len(model.samplings) == 1

    def test_constraint_before_connect(self, device_mm):
        """CONSTRAINT before CONNECT should parse due to unordered group"""
        model = device_mm.model_from_str("""
        DEVICE TestDevice WITH description="test", author="test";
        USE RaspberryPi_5_8GB;
        USE BME680[Sensor1];
        NETWORK[WiFi] WITH ssid="n", password="p";
        BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
        CONSTRAINT c1: count(SENSOR) >= 1;
        CONNECT Sensor1 WITH
            POWER gnd -- GND_1, vcc -- power_5v_a
            DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
            @ "test/topic";
        """)
        assert len(model.constraints) == 1


# ===========================================================================
# 7. Duplicate / Conflicting Clauses
# ===========================================================================


class TestDuplicateClauses:
    def test_multiple_device_declarations(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE Dev1 WITH description="a", author="a";
            DEVICE Dev2 WITH description="b", author="b";
            """)

    def test_multiple_networks(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            NETWORK[WiFi] WITH ssid="net1", password="pass1";
            NETWORK[WiFi] WITH ssid="net2", password="pass2";
            """)

    def test_duplicate_broker_names(self, device_mm):
        with pytest.raises(TextXSemanticError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            USE BME680[Sensor1];
            NETWORK[WiFi] WITH ssid="n", password="p";
            BROKER[MQTT] Same WITH host="a.com", port=1883, auth.username="u", auth.password="p";
            BROKER[MQTT] Same WITH host="b.com", port=1883, auth.username="u", auth.password="p";
            CONNECT Sensor1 WITH
                POWER gnd -- GND_1, vcc -- power_5v_a
                DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
                @ "test/topic";
            """)


# ===========================================================================
# 8. Special Characters & Encoding
# ===========================================================================


class TestSpecialCharacters:
    def test_unicode_in_string_values(self, device_mm):
        model = device_mm.model_from_str("""
        DEVICE TestDevice WITH description="Dispositif IoT avec des accents: \u00e9\u00e8\u00ea", author="Ren\u00e9";
        USE RaspberryPi_5_8GB;
        USE BME680[Sensor1];
        NETWORK[WiFi] WITH ssid="n", password="p";
        BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
        CONNECT Sensor1 WITH
            POWER gnd -- GND_1, vcc -- power_5v_a
            DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
            @ "test/topic";
        """)
        assert "\u00e9" in model.metadata.description

    def test_numeric_start_identifier_rejected(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE 123Bad WITH description="test", author="test";
            """)


# ===========================================================================
# 9. Alert Edge Cases
# ===========================================================================


class TestAlertEdgeCases:
    def test_alert_missing_then(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            ALERT myalert ON Sensor1 WHEN temperature > 50;
            """)

    def test_alert_missing_when(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            ALERT myalert ON Sensor1 THEN PUBLISH "alerts/hot";
            """)

    def test_alert_empty_actions(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            ALERT myalert ON Sensor1 WHEN temperature > 50 THEN;
            """)


# ===========================================================================
# 10. Constraint Edge Cases
# ===========================================================================


class TestConstraintEdgeCases:
    def test_constraint_missing_expression(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            CONSTRAINT empty:;
            """)

    def test_constraint_unknown_function(self, device_mm):
        """Unknown built-in function should fail at parse level"""
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            CONSTRAINT bad: unknown_func(SENSOR) > 0;
            """)

    def test_constraint_unknown_argument(self, device_mm):
        """Unknown function argument should fail at parse level"""
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            CONSTRAINT bad: count(UNKNOWN) > 0;
            """)


# ===========================================================================
# 11. SAMPLING Edge Cases
# ===========================================================================


class TestSamplingEdgeCases:
    def test_sampling_unknown_mode(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            SAMPLING Sensor1 WITH rate = 10 hz, mode = streaming;
            """)

    def test_sampling_missing_rate(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            SAMPLING Sensor1 WITH mode = continuous;
            """)

    def test_sampling_missing_unit(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str(VALID_PREAMBLE + """
            SAMPLING Sensor1 WITH rate = 10;
            """)


# ===========================================================================
# 12. SmartConnect Edge Cases
# ===========================================================================


class TestSmartConnectEdgeCases:
    def test_smartconnect_missing_semicolon(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            USE BME680[Sensor1];
            NETWORK[WiFi] WITH ssid="n", password="p";
            BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
            SMARTCONNECT Sensor1 @ "test/topic"
            """)

    def test_smartconnect_nonexistent_target(self, device_mm):
        with pytest.raises((TextXSemanticError, TextXSyntaxError)):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            NETWORK[WiFi] WITH ssid="n", password="p";
            BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
            SMARTCONNECT NonExistent @ "test/topic";
            """)


# ===========================================================================
# 13. Multiple Comments & Whitespace Stress
# ===========================================================================


class TestWhitespaceStress:
    def test_excessive_newlines(self, device_mm):
        spaced = VALID_PREAMBLE.replace(";", ";\n\n\n\n\n")
        model = device_mm.model_from_str(spaced)
        assert model.metadata.name == "TestDevice"

    def test_inline_comments_everywhere(self, device_mm):
        model = device_mm.model_from_str("""
        // Comment before DEVICE
        DEVICE TestDevice WITH description="test", author="test"; // inline
        // Comment before USE
        USE RaspberryPi_5_8GB; // board
        USE BME680[Sensor1]; // sensor
        NETWORK[WiFi] WITH ssid="n", password="p"; // network
        BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
        CONNECT Sensor1 WITH // connect
            POWER gnd -- GND_1, vcc -- power_5v_a // power
            DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
            @ "test/topic"; // topic
        // End
        """)
        assert model.metadata.name == "TestDevice"


# ===========================================================================
# 14. VIA Edge Cases
# ===========================================================================


class TestVIAEdgeCases:
    def test_via_nonexistent_broker(self, device_mm):
        with pytest.raises(TextXSemanticError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test";
            USE RaspberryPi_5_8GB;
            USE BME680[Sensor1];
            NETWORK[WiFi] WITH ssid="n", password="p";
            BROKER[MQTT] Cloud WITH host="cloud.io", port=1883, auth.username="u", auth.password="p";
            CONNECT Sensor1 WITH
                POWER gnd -- GND_1, vcc -- power_5v_a
                DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
                @ "test/topic"
                VIA NonExistentBroker;
            """)


# ===========================================================================
# 15. Operating System Variants
# ===========================================================================


class TestOSVariants:
    @pytest.mark.parametrize(
        "os_val",
        ["raspbian", "riotos", "freertos", "arduino", "esp-idf"],
    )
    def test_all_valid_os_values(self, device_mm, os_val):
        model = device_mm.model_from_str(
            f'DEVICE TestDevice WITH description="test", author="test", os={os_val};\n'
            "USE RaspberryPi_5_8GB;\n"
            "USE BME680[Sensor1];\n"
            'NETWORK[WiFi] WITH ssid="n", password="p";\n'
            'BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";\n'
            "CONNECT Sensor1 WITH\n"
            "    POWER gnd -- GND_1, vcc -- power_5v_a\n"
            "    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3\n"
            '    @ "test/topic";\n'
        )
        assert model.metadata.os == os_val

    def test_invalid_os_value(self, device_mm):
        with pytest.raises(TextXSyntaxError):
            device_mm.model_from_str("""
            DEVICE TestDevice WITH description="test", author="test", os=windows;
            """)
