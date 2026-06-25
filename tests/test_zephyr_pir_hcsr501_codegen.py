"""String-level emission tests for the PIR_HCSR501 Zephyr driver template.

Verifies that ``app/src/pir_hcsr501.c`` is emitted with the correct GPIO
init/read API calls and expected function symbols.
"""

from pathlib import Path
from textwrap import dedent

import pytest

from demol.transformations.m2t_zephyr import m2t_zephyr

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SYNTHETIC_PIR_MODEL = dedent("""\
    DEVICE SyntheticPir WITH description="pir codegen test", author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE PIR_HCSR501[Motion];

    CONNECT Motion WITH
        POWER gnd -- gnd, power_5v -- vcc
        DATA gpio[mode="input"] out -- d2
        @ "test.motion";
    """)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _generate(model_str: str, out: Path) -> None:
    from demol.lang.device import get_device_mm
    mm = get_device_mm()
    model = mm.model_from_str(model_str)
    m2t_zephyr(model, output_dir=str(out))


class TestPirFileEmission:
    """Verify that the expected driver files are created."""

    def test_pir_codegen_emits_c_file(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(SYNTHETIC_PIR_MODEL, out)
        c_file = out / "app" / "src" / "pir_hcsr501.c"
        assert c_file.exists(), f"Expected {c_file} to exist"

    def test_pir_codegen_emits_app_tree(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(SYNTHETIC_PIR_MODEL, out)
        assert (out / "app" / "CMakeLists.txt").exists()
        assert (out / "app" / "prj.conf").exists()
        assert (out / "app" / "src" / "main.c").exists()

    def test_pir_codegen_main_c_includes_driver(self, tmp_path) -> None:
        """The CMakeLists must list pir_hcsr501.c among sources."""
        out = tmp_path / "out"
        _generate(SYNTHETIC_PIR_MODEL, out)
        body = _read(out / "app" / "CMakeLists.txt")
        assert "pir_hcsr501.c" in body


class TestPirDriverContent:
    """Verify the generated C driver source."""

    def test_pir_driver_has_gpio_include(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(SYNTHETIC_PIR_MODEL, out)
        body = _read(out / "app" / "src" / "pir_hcsr501.c")
        assert '#include <zephyr/drivers/gpio.h>' in body

    def test_pir_driver_has_gpio_dt_spec(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(SYNTHETIC_PIR_MODEL, out)
        body = _read(out / "app" / "src" / "pir_hcsr501.c")
        assert "GPIO_DT_SPEC_GET" in body
        assert "demol_pir_hcsr501" in body

    def test_pir_driver_has_init_function(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(SYNTHETIC_PIR_MODEL, out)
        body = _read(out / "app" / "src" / "pir_hcsr501.c")
        assert "pir_hcsr501_init" in body
        assert "gpio_is_ready_dt" in body
        assert "gpio_pin_configure_dt" in body
        assert "GPIO_INPUT" in body

    def test_pir_driver_has_read_function(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(SYNTHETIC_PIR_MODEL, out)
        body = _read(out / "app" / "src" / "pir_hcsr501.c")
        assert "pir_hcsr501_read" in body
        assert "gpio_pin_get_dt" in body
        assert "bool *motion" in body or "bool* motion" in body
