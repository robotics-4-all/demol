"""Tests for multiple broker support and VIA routing."""

import warnings
import pytest
from textx import TextXSemanticError

CONN_DIST = """\
CONNECT Dist WITH
    POWER GND -- GND_1, VCC -- power_5v_a
    DATA gpio echo -- GPIO14, gpio trigger -- GPIO15
    @ "sensors/dist";
"""

BASE_MODEL = """\
DEVICE TestDevice WITH description="test", author="test", os=raspbian;
USE RaspberryPi_5_8GB;
USE HCSR04[Dist];
NETWORK[WiFi] WITH ssid="net", password="pass";
{brokers}
{connections}
"""


def _model(device_mm, brokers, connections=CONN_DIST):
    src = BASE_MODEL.format(brokers=brokers, connections=connections)
    return device_mm.model_from_str(src)


class TestSingleBrokerBackwardCompat:
    def test_single_broker_still_works(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[MQTT] Cloud WITH host="localhost", port=1883;',
            )
        assert m.broker is not None
        assert m.broker.name == "Cloud"
        assert len(m.brokers) == 1

    def test_model_broker_points_to_first(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[MQTT] First WITH host="localhost", port=1883;\n'
                'BROKER[AMQP] Second WITH host="localhost", port=5672;',
            )
        assert m.broker.name == "First"
        assert len(m.brokers) == 2


class TestMultipleBrokersParsing:
    def test_two_mqtt_brokers(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[MQTT] Local WITH host="localhost", port=1883;\n'
                'BROKER[MQTT] Cloud WITH host="cloud.example.com", port=1883, '
                'auth.username="u", auth.password="p";',
            )
        assert len(m.brokers) == 2
        assert m.brokers[0].name == "Local"
        assert m.brokers[1].name == "Cloud"

    def test_mixed_broker_types(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[MQTT] MqttBroker WITH host="localhost", port=1883;\n'
                'BROKER[AMQP] AmqpBroker WITH host="localhost", port=5672;\n'
                'BROKER[Redis] RedisBroker WITH host="localhost", port=6379;',
            )
        assert len(m.brokers) == 3
        names = [b.name for b in m.brokers]
        assert names == ["MqttBroker", "AmqpBroker", "RedisBroker"]


class TestDuplicateBrokerNames:
    def test_duplicate_broker_names_error(self, device_mm):
        with pytest.raises(TextXSemanticError, match="Duplicate broker name"):
            _model(
                device_mm,
                'BROKER[MQTT] SameName WITH host="localhost", port=1883;\n'
                'BROKER[AMQP] SameName WITH host="localhost", port=5672;',
            )


class TestVIARouting:
    def test_via_routes_to_specific_broker(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[MQTT] Local WITH host="localhost", port=1883;\n'
                'BROKER[MQTT] Cloud WITH host="cloud.example.com", port=1883, '
                'auth.username="u", auth.password="p";',
                "CONNECT Dist WITH\n"
                "    POWER GND -- GND_1, VCC -- power_5v_a\n"
                "    DATA gpio echo -- GPIO14, gpio trigger -- GPIO15\n"
                '    @ "sensors/dist"\n'
                "    VIA Cloud;",
            )
        conn = m.connections[0]
        assert conn.via == "Cloud"
        assert conn._resolved_broker.name == "Cloud"

    def test_via_defaults_to_first_broker(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[MQTT] Local WITH host="localhost", port=1883;\n'
                'BROKER[MQTT] Cloud WITH host="cloud.example.com", port=1883, '
                'auth.username="u", auth.password="p";',
            )
        conn = m.connections[0]
        assert getattr(conn, "via", None) is None or conn.via == ""
        assert conn._resolved_broker.name == "Local"

    def test_via_invalid_broker_error(self, device_mm):
        with pytest.raises(TextXSemanticError, match="VIA 'NonExistent'"):
            _model(
                device_mm,
                'BROKER[MQTT] Local WITH host="localhost", port=1883;',
                "CONNECT Dist WITH\n"
                "    POWER GND -- GND_1, VCC -- power_5v_a\n"
                "    DATA gpio echo -- GPIO14, gpio trigger -- GPIO15\n"
                '    @ "sensors/dist"\n'
                "    VIA NonExistent;",
            )

    def test_smartconnect_via(self, device_mm):
        src = """\
DEVICE TestDevice WITH description="test", author="test", os=raspbian;
USE RaspberryPi_5_8GB;
USE HCSR04[Dist];
NETWORK[WiFi] WITH ssid="net", password="pass";
BROKER[MQTT] Local WITH host="localhost", port=1883;
BROKER[MQTT] Cloud WITH host="cloud.example.com", port=1883, auth.username="u", auth.password="p";
SMARTCONNECT Dist @ "sensors/dist" VIA Cloud;
"""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = device_mm.model_from_str(src)
        sc = m.smartConnections[0]
        assert sc.via == "Cloud"

    def test_smartconnect_via_invalid_error(self, device_mm):
        src = """\
DEVICE TestDevice WITH description="test", author="test", os=raspbian;
USE RaspberryPi_5_8GB;
USE HCSR04[Dist];
NETWORK[WiFi] WITH ssid="net", password="pass";
BROKER[MQTT] Local WITH host="localhost", port=1883;
SMARTCONNECT Dist @ "sensors/dist" VIA BadName;
"""
        with pytest.raises(TextXSemanticError, match="VIA 'BadName'"):
            device_mm.model_from_str(src)


class TestTopicValidationPerBroker:
    def test_mqtt_topic_validated_against_mqtt_broker(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[MQTT] Local WITH host="localhost", port=1883;',
            )
        assert len(m.connections) == 1

    def test_amqp_topic_validated_against_amqp_broker(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[AMQP] Rabbit WITH host="localhost", port=5672;',
                "CONNECT Dist WITH\n"
                "    POWER GND -- GND_1, VCC -- power_5v_a\n"
                "    DATA gpio echo -- GPIO14, gpio trigger -- GPIO15\n"
                '    @ "sensors.distance";',
            )
        assert len(m.connections) == 1

    def test_via_routes_topic_validation_to_correct_broker(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[MQTT] MqttBroker WITH host="localhost", port=1883;\n'
                'BROKER[AMQP] AmqpBroker WITH host="localhost", port=5672;',
                "CONNECT Dist WITH\n"
                "    POWER GND -- GND_1, VCC -- power_5v_a\n"
                "    DATA gpio echo -- GPIO14, gpio trigger -- GPIO15\n"
                '    @ "sensors.distance"\n'
                "    VIA AmqpBroker;",
            )
        assert len(m.connections) == 1


class TestBrokerSecurityAllBrokers:
    def test_security_checked_for_all_brokers(self, device_mm):
        with pytest.raises(TextXSemanticError, match="without authentication"):
            _model(
                device_mm,
                'BROKER[MQTT] Local WITH host="localhost", port=1883;\n'
                'BROKER[MQTT] Insecure WITH host="remote.example.com", port=1883;',
            )

    def test_all_brokers_secure_passes(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[MQTT] Local WITH host="localhost", port=1883;\n'
                'BROKER[MQTT] Cloud WITH host="cloud.example.com", port=1883, '
                'auth.username="u", auth.password="p";',
            )
        assert len(m.brokers) == 2


class TestBrokerMap:
    def test_broker_map_populated(self, device_mm):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            m = _model(
                device_mm,
                'BROKER[MQTT] Alpha WITH host="localhost", port=1883;\n'
                'BROKER[AMQP] Beta WITH host="localhost", port=5672;',
            )
        assert "Alpha" in m._broker_map
        assert "Beta" in m._broker_map
        assert m._broker_map["Alpha"].host == "localhost"
        assert m._broker_map["Beta"].port == 5672
