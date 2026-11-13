"""Shared harness for Raspberry Pi runtime verification.

Levels covered here:

* L1 - generated tree imports with a flat, script-launchable layout
* L2 - broker contract: a generated node publishes real MQTT messages
* L3 - driver logic against emulated vendor libraries

No Raspberry Pi hardware is required for L1-L3; L2 needs Docker only to run
an ephemeral Eclipse Mosquitto broker.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

MOSQUITTO_CONF = """listener 1883 0.0.0.0
allow_anonymous true
persistence false
"""


def free_tcp_port() -> int:
    """Return a currently free TCP port on the loopback interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def broker_clause(host: str, port: int) -> str:
    """Broker declaration that passes the remote-broker security rule."""
    return f'host="{host}", port={port}, auth.username="demol", auth.password="demol"'


def generate_rpi(device_mm, model_path: Path, out_dir: Path) -> Path:
    """Generate RPi code for ``model_path`` into ``out_dir``."""
    from demol.transformations.m2t_rpi import m2t_rpi

    out_dir.mkdir(parents=True, exist_ok=True)
    model = device_mm.model_from_file(str(model_path))
    m2t_rpi(model, output_dir=str(out_dir))
    return out_dir


def write_fake_driver(
    path: Path, class_name: str, read_body: str, base: str = "Peripheral"
) -> None:
    """Overwrite a generated driver module with a deterministic fake.

    ``read_body`` is the body of ``read()``; it may use ``self._reads``.
    """
    path.write_text(
        "from peripheral import " + base + "\n"
        "\n"
        f"class {class_name}({base}):\n"
        "    def __init__(self):\n"
        f'        super().__init__(name="{class_name}", connections={{}}, attributes={{}})\n'
        "        self._reads = 0\n"
        "\n"
        "    def initialize(self):\n"
        "        pass\n"
        "\n"
        "    def disconnect(self):\n"
        "        pass\n"
        "\n"
        "    def read(self):\n"
        "        self._reads += 1\n"
        + "".join(f"        {line}\n" for line in read_body.strip().splitlines())
    )


def run_node(out_dir: Path, node_file: str, seconds: float = 2.5) -> str:
    """Run a generated node as a script, then terminate it. Returns output."""
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, node_file],
        cwd=str(out_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    try:
        time.sleep(seconds)
    finally:
        proc.terminate()
        try:
            output, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()
    return output or ""


class MqttCollector:
    """Collect MQTT messages from a live broker for assertions."""

    def __init__(self, host: str, port: int, topic: str = "#") -> None:
        import paho.mqtt.client as mqtt

        self.messages: list[tuple[str, object]] = []
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"demol-verify-{uuid.uuid4().hex[:10]}",
        )
        self._client.on_message = self._on_message
        self._client.connect(host, port, 10)
        self._client.loop_start()
        deadline = time.time() + 10
        while not self._client.is_connected() and time.time() < deadline:
            time.sleep(0.05)
        self._client.subscribe(topic, qos=1)
        time.sleep(0.3)

    def _on_message(self, _client, _userdata, msg) -> None:
        raw = msg.payload.decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            payload = raw
        self.messages.append((msg.topic, payload))

    def by_topic(self, topic: str) -> list:
        return [payload for name, payload in self.messages if name == topic]

    def count(self, topic: str) -> int:
        return len(self.by_topic(topic))

    def wait_for_count(self, topic: str, minimum: int, timeout: float = 5.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.count(topic) >= minimum:
                return True
            time.sleep(0.05)
        return False

    def publish(self, topic: str, payload: dict) -> None:
        self._client.publish(topic, json.dumps(payload), qos=1).wait_for_publish()

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()


@pytest.fixture(scope="session")
def mqtt_broker(tmp_path_factory):
    """Ephemeral Mosquitto broker in Docker; yields {'host', 'port'}."""
    if shutil.which("docker") is None:
        pytest.fail("docker is not available; L2 needs a broker container")

    config_dir = tmp_path_factory.mktemp("mosquitto")
    config = config_dir / "mosquitto.conf"
    config.write_text(MOSQUITTO_CONF)

    port = free_tcp_port()
    name = f"demol-verify-mqtt-{uuid.uuid4().hex[:10]}"
    run = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-p",
            f"127.0.0.1:{port}:1883",
            "-v",
            f"{config}:/mosquitto/config/mosquitto.conf:ro",
            "eclipse-mosquitto:2",
        ],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0:
        pytest.fail(f"could not start mosquitto: {run.stderr.strip()}")

    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("mosquitto did not become ready")
        yield {"host": "127.0.0.1", "port": port}
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
