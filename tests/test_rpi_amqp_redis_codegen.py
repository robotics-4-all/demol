"""T40 (AMQP) and T43 (Redis) broker codegen tests for the RPi backend.

Verifies that when a .dev model declares a BROKER[AMQP] or BROKER[Redis],
the RPi codegen emits a dedicated broker wrapper module and adds the
matching pip dependency to requirements.txt.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RPI_EXAMPLES_DIR = REPO_ROOT / "examples" / "rpi"


def _generate(model: Path, out: Path) -> None:
    res = subprocess.run(
        ["demol", "generate", "rpi", str(model), "--output-dir", str(out)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"generate failed: {res.stderr}"


def _read(out: Path, name: str) -> str:
    p = out / name
    assert p.is_file(), f"missing {name} under {out}"
    return p.read_text()


# ---------------------------------------------------------------------------
# T40: AMQP broker codegen for RPi
# ---------------------------------------------------------------------------


def test_rpi_amqp_broker_module_emitted(tmp_path):
    """A model with BROKER[AMQP] must produce amqp_broker.py alongside
    the standard msg.py + alerts.py + constraints.py."""
    model = RPI_EXAMPLES_DIR / "rpi_amqp_bme680.dev"
    if not model.is_file():
        pytest.skip(f"missing example: {model}")
    out = tmp_path / "amqp"
    _generate(model, out)
    content = _read(out, "amqp_broker.py")
    # Module-level expected symbols
    assert "amqp_publish" in content, "amqp_broker.py must define amqp_publish()"
    assert "pika" in content, "amqp_broker.py must reference pika"
    # Config baked in from the model
    assert "rabbit.local" in content, "amqp_broker.py must contain the model host"
    assert "/iot" in content, "amqp_broker.py must contain the vhost"
    assert "iot.sensors" in content, "amqp_broker.py must contain the topicExchange"
    assert "iot" in content, "amqp_broker.py must contain the username"
    # The module is import-clean (compiles)
    py_compile = subprocess.run(
        [sys.executable, "-m", "py_compile", str(out / "amqp_broker.py")],
        capture_output=True,
        text=True,
    )
    assert py_compile.returncode == 0, py_compile.stderr


def test_rpi_amqp_pip_dependency_added(tmp_path):
    """requirements.txt must include pika when an AMQP broker is declared."""
    model = RPI_EXAMPLES_DIR / "rpi_amqp_bme680.dev"
    if not model.is_file():
        pytest.skip(f"missing example: {model}")
    out = tmp_path / "amqp"
    _generate(model, out)
    reqs = _read(out, "requirements.txt")
    assert re.search(
        r"^pika", reqs, re.MULTILINE
    ), f"requirements.txt must include pika when AMQP is declared; got:\n{reqs}"


def test_rpi_amqp_not_emitted_for_mqtt_model(tmp_path):
    """Regression: an MQTT-only model must NOT emit amqp_broker.py."""
    mqtt_model = RPI_EXAMPLES_DIR / "multi_periph.dev"
    if not mqtt_model.is_file():
        pytest.skip(f"missing example: {mqtt_model}")
    out = tmp_path / "mqtt"
    _generate(mqtt_model, out)
    assert not (out / "amqp_broker.py").exists(), "amqp_broker.py must NOT be emitted when model has only MQTT brokers"
    assert not (
        out / "redis_broker.py"
    ).exists(), "redis_broker.py must NOT be emitted when model has only MQTT brokers"
    reqs = _read(out, "requirements.txt")
    assert "pika" not in reqs, "requirements.txt must NOT include pika for MQTT-only model"
    assert "redis" not in reqs, "requirements.txt must NOT include redis for MQTT-only model"


# ---------------------------------------------------------------------------
# T43: Redis broker codegen for RPi
# ---------------------------------------------------------------------------


def test_rpi_redis_broker_module_emitted(tmp_path):
    """A model with BROKER[Redis] must produce redis_broker.py."""
    model = RPI_EXAMPLES_DIR / "rpi_redis_bme680.dev"
    if not model.is_file():
        pytest.skip(f"missing example: {model}")
    out = tmp_path / "redis"
    _generate(model, out)
    content = _read(out, "redis_broker.py")
    assert "redis_publish" in content, "redis_broker.py must define redis_publish()"
    assert "redis.Redis" in content, "redis_broker.py must reference redis.Redis"
    # Config baked in
    assert "redis.local" in content, "redis_broker.py must contain the model host"
    assert "6379" in content, "redis_broker.py must contain the port"
    py_compile = subprocess.run(
        [sys.executable, "-m", "py_compile", str(out / "redis_broker.py")],
        capture_output=True,
        text=True,
    )
    assert py_compile.returncode == 0, py_compile.stderr


def test_rpi_redis_pip_dependency_added(tmp_path):
    """requirements.txt must include redis when a Redis broker is declared."""
    model = RPI_EXAMPLES_DIR / "rpi_redis_bme680.dev"
    if not model.is_file():
        pytest.skip(f"missing example: {model}")
    out = tmp_path / "redis"
    _generate(model, out)
    reqs = _read(out, "requirements.txt")
    assert re.search(
        r"^redis", reqs, re.MULTILINE
    ), f"requirements.txt must include redis when Redis is declared; got:\n{reqs}"


def test_rpi_get_broker_config_redis_kind():
    """get_broker_config() must return kind='redis' and the db field."""
    from demol.lang import get_device_mm
    from demol.transformations.m2t_rpi import RPiCodeGenerator

    model = get_device_mm().model_from_file(str(RPI_EXAMPLES_DIR / "rpi_redis_bme680.dev"))
    gen = RPiCodeGenerator(model, Path("/tmp/_unused"))
    redis_broker = next(b for b in gen.get_brokers() if type(b).__name__ == "RedisBroker")
    cfg = gen.get_broker_config(redis_broker)
    assert cfg["kind"] == "redis"
    assert cfg["host"] == "redis.local"
    assert cfg["port"] == 6379
    assert cfg["db"] == 0
    assert cfg["username"] == "iot"
    assert cfg["password"] == "iotpass"


def test_rpi_get_broker_config_amqp_kind():
    """get_broker_config() must return kind='amqp' and the AMQP-specific fields."""
    from demol.lang import get_device_mm
    from demol.transformations.m2t_rpi import RPiCodeGenerator

    model = get_device_mm().model_from_file(str(RPI_EXAMPLES_DIR / "rpi_amqp_bme680.dev"))
    gen = RPiCodeGenerator(model, Path("/tmp/_unused"))

    amqp_broker = next(b for b in gen.get_brokers() if type(b).__name__ == "AMQPBroker")
    cfg = gen.get_broker_config(amqp_broker)
    assert cfg["kind"] == "amqp"
    assert cfg["host"] == "rabbit.local"
    assert cfg["port"] == 5672
    assert cfg["vhost"] == "/iot"
    assert cfg["topic_exchange"] == "iot.sensors"
    assert cfg["username"] == "iot"
    assert cfg["password"] == "iotpass"
