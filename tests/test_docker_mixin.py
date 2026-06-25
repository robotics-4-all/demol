"""Tests for the shared :class:`DockerBuildMixin`.

These tests pin the contract that :class:`DockerBuildMixin` works for both
the RPi and the RIOT backends, that the per-file renderers produce the
expected artifacts, and that the byte-level output is stable across calls
(idempotent regeneration, identical file contents across calls in the same
process). They also exercise the mixin against a minimal in-test backend
to prove the contract is sufficient for new OSes.
"""

import os
import stat
from pathlib import Path
from typing import Any, Dict

import jinja2
import pytest

from demol.lang.device import get_device_mm
from demol.transformations.base_generator import BaseCodeGenerator
from demol.transformations.docker_mixin import DockerBuildMixin
from demol.transformations.m2t_riot import m2t_riot
from demol.transformations.m2t_rpi import m2t_rpi

# --- Shared device-model fixtures -----------------------------------------


RPI_MODEL = """
DEVICE MixTest WITH description="docker mixin test", author="tester", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680 [EnvSensor], LedGeneric [StatusLed];
NETWORK [WiFi] WITH ssid="ssid", password="pass";
BROKER [MQTT] MyBroker WITH host="localhost", port=1883;
CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c [slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";
SMARTCONNECT StatusLed @ "actuators/led";
"""


RIOT_MODEL = """
DEVICE RiotMixinTest WITH description="docker mixin test", author="tester", os=riotos;
USE ESP32Wroom32;
USE BME680 [EnvSensor], LedGeneric [StatusLed];
NETWORK [WiFi] WITH ssid="ssid", password="pass";
BROKER [MQTT] MyBroker WITH host="localhost", port=1883;
CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- VCC_5V
    DATA i2c [slave_address=0x77] sda sda -- GPIO21, scl scl -- GPIO22
    @ "sensors/env";
SMARTCONNECT StatusLed @ "actuators/led";
"""


@pytest.fixture
def rpi_model():
    return get_device_mm().model_from_str(RPI_MODEL)


@pytest.fixture
def riot_model():
    return get_device_mm().model_from_str(RIOT_MODEL)


def test_rpi_docker_files_via_mixin(tmp_path, rpi_model):
    """RPi generator uses the mixin to render all four Docker artifacts."""
    out = tmp_path / "rpi"
    m2t_rpi(rpi_model, output_dir=str(out))

    assert (out / "Dockerfile").is_file()
    assert (out / "requirements.txt").is_file()
    assert (out / "docker-compose.yml").is_file()
    assert (out / "install_deps.sh").is_file()

    assert "FROM python:3.9-slim" in (out / "Dockerfile").read_text()
    assert "commlib-py" in (out / "requirements.txt").read_text()
    assert "version: '3.8'" in (out / "docker-compose.yml").read_text()
    assert "apt-get install" in (out / "install_deps.sh").read_text()


def test_rpi_install_deps_is_executable(tmp_path, rpi_model):
    out = tmp_path / "rpi"
    m2t_rpi(rpi_model, output_dir=str(out))
    mode = stat.S_IMODE(os.stat(out / "install_deps.sh").st_mode)
    assert mode & 0o111, f"install_deps.sh must be executable, got mode {oct(mode)}"


def test_rpi_render_individually(tmp_path, rpi_model):
    """Per-file renderers can be called in isolation."""
    from demol.transformations.m2t_rpi import RPiCodeGenerator

    out = tmp_path / "rpi"
    gen = RPiCodeGenerator(rpi_model, out)
    gen.generate_common()
    gen.generate_messages()
    gen._render_dockerfile()
    gen._render_requirements()
    gen._render_compose()
    gen._render_install_deps()

    assert (out / "Dockerfile").is_file()
    assert (out / "requirements.txt").is_file()
    assert (out / "docker-compose.yml").is_file()
    assert (out / "install_deps.sh").is_file()


def test_rpi_install_deps_os_specific_packages(tmp_path, rpi_model):
    """os_specific_packages is forwarded into the install_deps context."""
    from demol.transformations.m2t_rpi import RPiCodeGenerator

    out = tmp_path / "rpi"
    gen = RPiCodeGenerator(rpi_model, out)
    gen._render_install_deps(os_specific_packages=["libfoo-dev", "libbar-dev"])

    assert (out / "install_deps.sh").is_file()
    mode = stat.S_IMODE(os.stat(out / "install_deps.sh").st_mode)
    assert mode & 0o111


def test_rpi_byte_identical_to_baseline(tmp_path):
    """The RPi mixin produces output identical to the pre-refactor baseline."""
    baseline_dir = (
        Path(__file__).parent.parent / ".matrixx" / "baselines" / "wave1_pre_refactor" / "rpi" / "multi_periph"
    )
    example_path = Path(__file__).parent.parent / "examples" / "rpi" / "multi_periph.dev"
    if not baseline_dir.is_dir() or not example_path.is_file():
        pytest.skip(f"baseline or example missing: {baseline_dir} / {example_path}")

    model = get_device_mm().model_from_file(str(example_path))
    out = tmp_path / "rpi"
    m2t_rpi(model, output_dir=str(out))

    for name in ("Dockerfile", "requirements.txt", "docker-compose.yml", "install_deps.sh"):
        assert (out / name).read_bytes() == (baseline_dir / name).read_bytes(), name


def test_riot_docker_files_via_mixin(tmp_path, riot_model):
    """RIOT generator uses the mixin to render both Docker artifacts."""
    out = tmp_path / "riot"
    m2t_riot(riot_model, output_dir=str(out))

    assert (out / "Dockerfile.riotbuild").is_file()
    assert (out / "build_docker.sh").is_file()

    assert "FROM riot/riotbuild:latest" in (out / "Dockerfile.riotbuild").read_text()
    assert "ARG RIOT_VERSION=" in (out / "Dockerfile.riotbuild").read_text()
    assert "docker build" in (out / "build_docker.sh").read_text()


def test_riot_build_script_is_executable(tmp_path, riot_model):
    out = tmp_path / "riot"
    m2t_riot(riot_model, output_dir=str(out))
    mode = stat.S_IMODE(os.stat(out / "build_docker.sh").st_mode)
    assert mode & 0o111, f"build_docker.sh must be executable, got mode {oct(mode)}"


def test_riot_render_individually(tmp_path, riot_model):
    """Per-file renderers can be called in isolation for the RIOT path."""
    from demol.transformations.m2t_riot import RiotCodeGenerator

    out = tmp_path / "riot"
    gen = RiotCodeGenerator(riot_model, out)
    gen._global_context = gen.build_global_context()
    gen._render_riot_dockerfile()
    gen._render_riot_build_script()

    assert (out / "Dockerfile.riotbuild").is_file()
    assert (out / "build_docker.sh").is_file()


def test_riot_byte_identical_to_baseline(tmp_path):
    """The RIOT mixin produces output identical to the pre-refactor baseline."""
    baseline_dir = (
        Path(__file__).parent.parent / ".matrixx" / "baselines" / "wave1_pre_refactor" / "riot" / "esp_iot_device"
    )
    example_path = Path(__file__).parent.parent / "examples" / "esp" / "esp_iot_device.dev"
    if not baseline_dir.is_dir() or not example_path.is_file():
        pytest.skip(f"baseline or example missing: {baseline_dir} / {example_path}")

    model = get_device_mm().model_from_file(str(example_path))
    out = tmp_path / "riot"
    m2t_riot(model, output_dir=str(out))

    for name in ("Dockerfile.riotbuild", "build_docker.sh"):
        assert (out / name).read_bytes() == (baseline_dir / name).read_bytes(), name


class _FakeBackend(BaseCodeGenerator, DockerBuildMixin):
    """Minimal backend used to assert the mixin's extension contract.

    Reuses the ``raspbian`` OS slot to exercise the full RPi dispatcher
    path (Dockerfile + requirements + compose + install_deps).
    """

    OS = "raspbian"

    def __init__(self, device_model, output_dir: Path, jinja_env: jinja2.Environment):
        super().__init__(device_model, output_dir)
        self.env = jinja_env

    def setup_template_environment(self) -> jinja2.Environment:
        return self.env

    def generate(self) -> None:
        self.generate_docker_files()

    def _build_docker_context(self) -> Dict[str, Any]:
        return {
            "apt_dependencies": ["pkg-fake-a", "pkg-fake-b"],
            "dependencies": ["pyfake"],
            "connections": [],
        }


def test_mixin_dispatches_to_fake_backend(tmp_path):
    """A custom backend inheriting DockerBuildMixin works out of the box."""
    jinja_env = jinja2.Environment(
        loader=jinja2.DictLoader(
            {
                "Dockerfile.j2": "{% for p in apt_dependencies %}{{ p }}\n{% endfor %}",
                "requirements.txt.j2": "{% for d in dependencies %}{{ d }}\n{% endfor %}",
                "docker-compose.yml.j2": "version: '3.8'\nservices: {}\n",
                "install_deps.sh.j2": "#!/bin/bash\n{% for p in apt_dependencies %}apt-get install -y {{ p }}\n{% endfor %}",
            }
        )
    )
    backend = _FakeBackend(device_model=None, output_dir=tmp_path, jinja_env=jinja_env)
    backend.generate()

    assert (tmp_path / "Dockerfile").read_text() == "pkg-fake-a\npkg-fake-b\n"
    assert (tmp_path / "requirements.txt").read_text() == "pyfake\n"
    assert (tmp_path / "docker-compose.yml").is_file()
    assert (tmp_path / "install_deps.sh").is_file()


def test_mixin_skips_unknown_os(tmp_path):
    """OS values not in the dispatch table produce no Docker files."""

    class _NoDockerBackend(_FakeBackend):
        OS = "no-docker-here"

        def _has_docker_for_os(self, os_name: str) -> bool:
            return False

    jinja_env = jinja2.Environment(loader=jinja2.DictLoader({}))
    backend = _NoDockerBackend(device_model=None, output_dir=tmp_path, jinja_env=jinja_env)
    backend.generate()
    assert list(tmp_path.iterdir()) == []


def test_mixin_default_context_raises(tmp_path):
    """The mixin's default ``_build_docker_context`` raises NotImplementedError."""

    class _Stub(BaseCodeGenerator, DockerBuildMixin):
        OS = "raspbian"

        def __init__(self, output_dir: Path):
            self.device_model = None
            self.output_dir = output_dir
            self.env = jinja2.Environment(loader=jinja2.DictLoader({}))

        def setup_template_environment(self):
            return self.env

        def generate(self):
            pass

    stub = _Stub(tmp_path)
    with pytest.raises(NotImplementedError):
        stub._build_docker_context()


def test_mixin_renderers_use_inherited_writer(tmp_path):
    """Per-file renderers call ``self._write_template`` from BaseCodeGenerator."""
    jinja_env = jinja2.Environment(
        loader=jinja2.DictLoader(
            {
                "Dockerfile.j2": "fake-Dockerfile",
                "requirements.txt.j2": "fake-requirements",
                "docker-compose.yml.j2": "fake-compose",
                "install_deps.sh.j2": "fake-install-deps",
            }
        )
    )
    backend = _FakeBackend(device_model=None, output_dir=tmp_path, jinja_env=jinja_env)

    backend._render_dockerfile()
    backend._render_requirements()
    backend._render_compose()
    backend._render_install_deps()

    assert (tmp_path / "Dockerfile").read_text() == "fake-Dockerfile"
    assert (tmp_path / "requirements.txt").read_text() == "fake-requirements"
    assert (tmp_path / "docker-compose.yml").read_text() == "fake-compose"
    assert (tmp_path / "install_deps.sh").read_text() == "fake-install-deps"


def test_mixin_renders_to_alternate_output_dir(tmp_path, rpi_model):
    """``output_dir`` argument overrides ``self.output_dir`` for one-off renders."""
    from demol.transformations.m2t_rpi import RPiCodeGenerator

    primary = tmp_path / "primary"
    alternate = tmp_path / "alternate"
    primary.mkdir()
    alternate.mkdir()

    gen = RPiCodeGenerator(rpi_model, primary)
    gen._render_dockerfile(output_dir=alternate)

    assert (alternate / "Dockerfile").is_file()
    assert not (primary / "Dockerfile").exists()
