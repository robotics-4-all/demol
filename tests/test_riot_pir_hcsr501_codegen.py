"""String-level emission tests for the PIR_HCSR501 RIOT driver template.

Verifies that ``sensor_pir_hcsr501_N.c`` and ``sensor_pir_hcsr501_N.h`` are
emitted with the correct GPIO init/read API calls and that the JSON output
contains the expected ``motion`` and ``state`` fields.
"""

from pathlib import Path

from demol.lang.device import get_device_mm
from demol.transformations.m2t_riot import m2t_riot


BASE_MODEL = """
DEVICE PirTest WITH
    description="PIR HC-SR501 motion sensor test",
    author="tester",
    os=riotos;

USE ESP32Wroom32;
USE PIR_HCSR501 [Motion];

NETWORK[WiFi] WITH ssid="ssid", password="pass";

BROKER[MQTT] MyBroker WITH
    host="localhost",
    port=1883,
    auth.username="guest",
    auth.password="guest";

CONNECT Motion WITH
    POWER VCC -- VCC_5V, GND -- GND_1
    DATA gpio[mode="input"] OUT -- GPIO11
    @ "sensors/pir";
"""


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _generate(model_str: str, out: Path) -> None:
    mm = get_device_mm()
    model = mm.model_from_str(model_str)
    m2t_riot(model, output_dir=str(out))


class TestPirFileEmission:
    """Verify that the expected driver files are created."""

    def test_pir_codegen_emits_c_and_h(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        c_file = out / "sensor_pir_hcsr501_0.c"
        h_file = out / "sensor_pir_hcsr501_0.h"
        assert c_file.exists(), f"Expected {c_file} to exist"
        assert h_file.exists(), f"Expected {h_file} to exist"

    def test_pir_codegen_emits_periph_gpio_include(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_pir_hcsr501_0.c")
        assert '#include "periph/gpio.h"' in body


class TestPirHeaderContent:
    """Verify the generated header file."""

    def test_pir_header_has_guard(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_pir_hcsr501_0.h")
        assert "#ifndef PIR_HCSR501_0_DRIVER_H" in body
        assert "#define PIR_HCSR501_0_DRIVER_H" in body

    def test_pir_header_declares_functions(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_pir_hcsr501_0.h")
        assert "init_sensor_pir_hcsr501_0" in body
        assert "start_sensor_pir_hcsr501_0" in body
        assert "pir_hcsr501_0_callback" in body

    def test_pir_header_has_freq_define(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_pir_hcsr501_0.h")
        assert "#define PIR_HCSR501_0_FREQ" in body


class TestPirSourceContent:
    """Verify the generated C source code."""

    def test_pir_c_has_gpio_init(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_pir_hcsr501_0.c")
        assert "gpio_init(" in body
        assert "GPIO_IN" in body

    def test_pir_c_has_gpio_read(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_pir_hcsr501_0.c")
        assert "gpio_read(" in body

    def test_pir_c_has_motion_json_key(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_pir_hcsr501_0.c")
        assert 'JSON_KEY, "motion", JSON_INT' in body

    def test_pir_c_has_state_json_key(self, tmp_path) -> None:
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        body = _read(out / "sensor_pir_hcsr501_0.c")
        assert '"state", JSON_INT, state' in body
