"""Wave 4 peripheral porting tests — T30 relay, T32 servo, T34 ads1115, T36 shtc3 (RIOT) + Zephyr variants.

Verifies that each new peripheral .hwd TEMPLATES entry resolves to a
concrete .c.j2 file and that ``demol generate`` produces the expected
driver file under the correct output filename.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples" / "esp"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "demol" / "templates"


def _generate(model: Path, out_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["demol", "generate", "riot", str(model), "--output-dir", str(out_dir)],
        capture_output=True,
        text=True,
    )


def _generate_zephyr(model: Path, out_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["demol", "generate", "zephyr", str(model), "--output-dir", str(out_dir)],
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("example,tpl_rel", [
    ("esp_relay.dev", "riot/actuator_relay.c.j2"),
    ("esp_servo.dev", "riot/actuator_servo.c.j2"),
    ("esp_ads1115.dev", "riot/sensor_ads1115.c.j2"),
    ("esp_shtc3.dev", "riot/sensor_shtc3.c.j2"),
])
def test_riot_template_exists(example, tpl_rel):
    assert (TEMPLATES_DIR / tpl_rel).is_file(), f"Missing {tpl_rel}"


@pytest.mark.parametrize("example,tpl_rel", [
    ("wemos_relay.dev", "zephyr/relay.c.j2"),
    ("wemos_servo.dev", "zephyr/servo.c.j2"),
    ("wemos_ads1115.dev", "zephyr/ads1115.c.j2"),
    ("wemos_shtc3.dev", "zephyr/shtc3.c.j2"),
    ("wemos_hw006.dev", "zephyr/hw006.c.j2"),
])
def test_zephyr_template_exists(example, tpl_rel):
    assert (TEMPLATES_DIR / tpl_rel).is_file(), f"Missing {tpl_rel}"


@pytest.mark.parametrize("example,output_glob", [
    ("esp_relay.dev", "actuator_relay_0.c"),
    ("esp_servo.dev", "actuator_servo_0.c"),
    ("esp_ads1115.dev", "sensor_ads1115_0.c"),
    ("esp_shtc3.dev", "sensor_shtc3_0.c"),
])
def test_riot_generate_produces_driver(example, output_glob, tmp_path):
    model = EXAMPLES_DIR / example
    if not model.is_file():
        pytest.skip(f"example {example} not present")
    out = tmp_path / "out"
    res = _generate(model, out)
    assert res.returncode == 0, res.stderr
    matches = list(out.rglob(output_glob))
    assert matches, f"Expected {output_glob} under {out}; got {list(out.rglob('*'))[:5]}"


@pytest.mark.parametrize("example,output_glob", [
    ("wemos_relay.dev", "relay_0.c"),
    ("wemos_servo.dev", "servo_0.c"),
    ("wemos_ads1115.dev", "ads1115_0.c"),
    ("wemos_shtc3.dev", "shtc3_0.c"),
    ("wemos_hw006.dev", "hw006_0.c"),
])
def test_zephyr_generate_produces_driver(example, output_glob, tmp_path):
    model = EXAMPLES_DIR / example
    if not model.is_file():
        pytest.skip(f"example {example} not present")
    out = tmp_path / "out"
    res = _generate_zephyr(model, out)
    assert res.returncode == 0, res.stderr
    matches = list(out.rglob(output_glob))
    assert matches, f"Expected {output_glob} under {out}"
