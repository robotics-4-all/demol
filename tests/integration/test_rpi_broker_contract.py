"""L2: generated nodes must deliver readings to the configured broker.

Each test generates code from a real model, replaces the hardware driver with a
deterministic fake, runs the generated node as a script, and asserts what a
subscriber observes on a live Mosquitto broker.
"""

from __future__ import annotations

import json
import time

import pytest

from rpi_harness import (
    MqttCollector,
    broker_clause,
    generate_rpi,
    run_node,
    write_fake_driver,
)

pytestmark = pytest.mark.integration

SENSOR_MODEL = """
DEVICE {name} WITH description="e2e", author="demol", os=raspbian;
USE RaspberryPi_4B_4GB;
USE BME680[EnvSensor];
NETWORK[WiFi] WITH ssid="n", password="p";
BROKER[MQTT] Local WITH {broker};
CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/environment";
{extra}
"""

ACTUATOR_MODEL = """
DEVICE {name} WITH description="e2e", author="demol", os=raspbian;
USE RaspberryPi_4B_4GB;
USE LedGeneric[StatusLed];
NETWORK[WiFi] WITH ssid="n", password="p";
BROKER[MQTT] Local WITH {broker};
CONNECT StatusLed WITH
    POWER gnd -- GND_3, vcc -- power_3v3_a
    DATA gpio[mode="output"] vin -- GPIO17
    @ "actuators/status";
"""

TOPIC = "sensors/environment"


def _prepare(device_mm, tmp_path, name, broker, extra=""):
    model_path = tmp_path / f"{name}.dev"
    model_path.write_text(
        SENSOR_MODEL.format(name=name, broker=broker_clause(**broker), extra=extra),
        encoding="utf-8",
    )
    out_dir = tmp_path / f"{name}_out"
    generate_rpi(device_mm, model_path, out_dir)
    return out_dir


def _fake_env_reading(temperature=21.5):
    return (
        "self.update_state_data({"
        f'"temperature": {temperature}, '
        '"pressure": 1009.25, '
        '"humidity": 44.5, '
        '"gas_resistance": 33333.0'
        "})"
    )


def test_continuous_sensor_publishes_expected_payload(device_mm, mqtt_broker, tmp_path):
    out_dir = _prepare(device_mm, tmp_path, "ContinuousDemo", mqtt_broker)
    write_fake_driver(
        out_dir / "bme680_envsensor.py", "BME680_EnvSensor", _fake_env_reading()
    )

    collector = MqttCollector(mqtt_broker["host"], mqtt_broker["port"])
    try:
        output = run_node(out_dir, "envsensor_node.py", seconds=2.0)
        assert collector.wait_for_count(TOPIC, 3, timeout=5.0), collector.messages
    finally:
        collector.close()

    assert "Traceback" not in output, output
    payloads = collector.by_topic(TOPIC)
    assert payloads, "no reading reached the broker"
    sample = payloads[0]
    assert sample["temperature"] == pytest.approx(21.5)
    assert sample["pressure"] == pytest.approx(1009.25)
    assert sample["humidity"] == pytest.approx(44.5)
    assert sample["gas_resistance"] == pytest.approx(33333.0)
    assert sample["header"]["timestamp"] > 0

    stamps = [payload["header"]["timestamp"] for payload in payloads]
    assert stamps == sorted(stamps), "messages were published out of order"


def test_on_change_publishes_only_when_threshold_is_crossed(
    device_mm, mqtt_broker, tmp_path
):
    extra = "SAMPLING EnvSensor WITH rate = 20 hz, mode = on_change, threshold = 2.0;"
    out_dir = _prepare(device_mm, tmp_path, "OnChangeDemo", mqtt_broker, extra=extra)
    write_fake_driver(
        out_dir / "bme680_envsensor.py",
        "BME680_EnvSensor",
        "temperature = 21.5 if self._reads < 3 else 30.0\n"
        + _fake_env_reading("temperature"),
    )

    collector = MqttCollector(mqtt_broker["host"], mqtt_broker["port"])
    try:
        output = run_node(out_dir, "envsensor_node.py", seconds=2.0)
        collector.wait_for_count(TOPIC, 2, timeout=5.0)
        time.sleep(0.3)
    finally:
        collector.close()

    assert "Traceback" not in output, output
    payloads = collector.by_topic(TOPIC)
    assert 2 <= len(payloads) <= 3, payloads
    temperatures = {payload["temperature"] for payload in payloads}
    assert temperatures == {21.5, 30.0}


def test_batch_publishes_complete_buffers(device_mm, mqtt_broker, tmp_path):
    extra = "SAMPLING EnvSensor WITH rate = 10 hz, mode = batch, buffer = 5;"
    out_dir = _prepare(device_mm, tmp_path, "BatchDemo", mqtt_broker, extra=extra)
    write_fake_driver(
        out_dir / "bme680_envsensor.py", "BME680_EnvSensor", _fake_env_reading()
    )

    collector = MqttCollector(mqtt_broker["host"], mqtt_broker["port"])
    try:
        output = run_node(out_dir, "envsensor_node.py", seconds=2.0)
        collector.wait_for_count(TOPIC, 5, timeout=5.0)
        time.sleep(0.3)
    finally:
        collector.close()

    assert "Traceback" not in output, output
    count = collector.count(TOPIC)
    assert count >= 5, collector.messages
    assert count % 5 == 0, f"partial batch published: {count}"


def test_alert_publishes_to_its_topic(device_mm, mqtt_broker, tmp_path):
    extra = (
        "ALERT hot ON EnvSensor WHEN temperature > 20 "
        'THEN PUBLISH "alerts/hot" VIA Local COOLDOWN 1 hz;'
    )
    out_dir = _prepare(device_mm, tmp_path, "AlertDemo", mqtt_broker, extra=extra)
    write_fake_driver(
        out_dir / "bme680_envsensor.py", "BME680_EnvSensor", _fake_env_reading(30.0)
    )

    collector = MqttCollector(mqtt_broker["host"], mqtt_broker["port"])
    try:
        output = run_node(out_dir, "envsensor_node.py", seconds=3.0)
        assert collector.wait_for_count("alerts/hot", 1, timeout=5.0), (
            collector.messages
        )
    finally:
        collector.close()

    assert "Traceback" not in output, output
    alert = collector.by_topic("alerts/hot")[0]
    assert alert["alert"] == "hot"
    assert alert["source"] == "EnvSensor"
    assert alert["data"]["temperature"] == pytest.approx(30.0)


def test_actuator_node_receives_commands(device_mm, mqtt_broker, tmp_path):
    model_path = tmp_path / "ActuatorDemo.dev"
    model_path.write_text(
        ACTUATOR_MODEL.format(name="ActuatorDemo", broker=broker_clause(**mqtt_broker)),
        encoding="utf-8",
    )
    out_dir = tmp_path / "ActuatorDemo_out"
    generate_rpi(device_mm, model_path, out_dir)

    (out_dir / "ledgeneric_statusled.py").write_text(
        "from peripheral import Actuator\n"
        "\n"
        "class LedGeneric_StatusLed(Actuator):\n"
        "    def initialize(self):\n"
        "        pass\n"
        "\n"
        "    def disconnect(self):\n"
        "        pass\n"
        "\n"
        "    def write(self, msg):\n"
        '        with open("actuator_writes.log", "a", encoding="utf-8") as handle:\n'
        "            handle.write(f\"{getattr(msg, 'state', None)}\\n\")\n",
        encoding="utf-8",
    )

    import subprocess
    import sys

    node = subprocess.Popen(
        [sys.executable, "statusled_node.py"],
        cwd=str(out_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    collector = MqttCollector(mqtt_broker["host"], mqtt_broker["port"])
    log = out_dir / "actuator_writes.log"
    try:
        deadline = time.time() + 10
        while time.time() < deadline and not log.exists():
            collector.publish("actuators/status", {"state": True, "brightness": 0.5})
            time.sleep(0.25)
    finally:
        node.terminate()
        output, _ = node.communicate(timeout=10)
        collector.close()

    assert "Traceback" not in output, output
    assert log.is_file(), output
    assert "True" in log.read_text(encoding="utf-8")


def test_generated_messages_are_json_objects(device_mm, mqtt_broker, tmp_path):
    out_dir = _prepare(device_mm, tmp_path, "JsonDemo", mqtt_broker)
    write_fake_driver(
        out_dir / "bme680_envsensor.py", "BME680_EnvSensor", _fake_env_reading()
    )

    collector = MqttCollector(mqtt_broker["host"], mqtt_broker["port"])
    try:
        run_node(out_dir, "envsensor_node.py", seconds=2.0)
        collector.wait_for_count(TOPIC, 1, timeout=5.0)
    finally:
        collector.close()

    assert collector.by_topic(TOPIC), collector.messages
    for payload in collector.by_topic(TOPIC):
        assert isinstance(payload, dict), payload
        json.dumps(payload)
