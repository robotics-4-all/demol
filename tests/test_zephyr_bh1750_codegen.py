"""Zephyr BH1750 (light sensor) code generation tests.

Verifies the Zephyr backend emits a valid bh1750.c driver, that it uses
the Zephyr sensor API (sensor_sample_fetch / SENSOR_CHAN_LIGHT), and
that the devicetree overlay references the correct compatible string.
"""

from pathlib import Path
from textwrap import dedent

import pytest

from demol.transformations.m2t_zephyr import m2t_zephyr

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SYNTHETIC_BH1750_MODEL = dedent("""\
    DEVICE SyntheticBh1750 WITH description="bh1750 codegen test", author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BH1750[Light];

    CONNECT Light WITH
        POWER GND -- gnd, VCC -- power_3v3
        DATA i2c[slave_address=0x23] sda sda -- d2, scl scl -- d1
        @ "test.bh1750";
    """)


@pytest.fixture(scope="module")
def synthetic_bh1750_dir(device_mm, tmp_path_factory):
    """Generate a Zephyr app tree from the synthetic BH1750 model."""
    out = tmp_path_factory.mktemp("zephyr_synthetic_bh1750")
    model = device_mm.model_from_str(SYNTHETIC_BH1750_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


def _has_cpp() -> bool:
    import shutil

    return shutil.which("cpp") is not None


def _has_clang_format() -> bool:
    import shutil

    return shutil.which("clang-format") is not None


def _validate_c_syntax(c_file: Path) -> tuple:
    """Validate C syntax for one generated .c file.

    Returns ``(tool_name, ok, message)``. Prefers ``cpp -fsyntax-only``
    with the local Zephyr stub headers; falls back to ``clang-format``
    when cpp is missing.
    """
    import subprocess

    zephyr_stubs_dir = PROJECT_ROOT / "tests" / "fixtures" / "zephyr_stubs"

    if _has_cpp() and zephyr_stubs_dir.is_dir():
        cmd = ["cpp", "-fsyntax-only", f"-I{zephyr_stubs_dir}", str(c_file)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return ("cpp -fsyntax-only", True, "")
        return (
            "cpp -fsyntax-only",
            False,
            f"{proc.stderr.strip() or proc.stdout.strip()}",
        )
    if _has_clang_format():
        cmd = ["clang-format", str(c_file)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return ("clang-format", True, "")
        return (
            "clang-format",
            False,
            f"clang-format failed to lex {c_file.name}: {proc.stderr.strip()[:200]}",
        )
    return ("", False, "no C toolchain available")


# --- Test cases (≥3) ---


def test_bh1750_driver_emitted(synthetic_bh1750_dir):
    """Verify bh1750.c is generated in the Zephyr app tree."""
    bh1750 = synthetic_bh1750_dir / "app" / "src" / "bh1750.c"
    assert bh1750.is_file(), "bh1750.c was not generated"
    assert bh1750.stat().st_size > 0, "bh1750.c is empty"


def test_bh1750_driver_uses_zephyr_sensor_api(synthetic_bh1750_dir):
    """Assert bh1750.c uses sensor_sample_fetch, DEVICE_DT_GET, SENSOR_CHAN_LIGHT."""
    bh1750 = synthetic_bh1750_dir / "app" / "src" / "bh1750.c"
    assert bh1750.is_file(), "bh1750.c not found"

    body = bh1750.read_text(encoding="utf-8")
    assert "sensor_sample_fetch" in body, "missing sensor_sample_fetch"
    assert "DEVICE_DT_GET" in body, "missing DEVICE_DT_GET"
    assert "SENSOR_CHAN_LIGHT" in body, "missing SENSOR_CHAN_LIGHT"
    assert "rohm_bh1750" in body, "missing rohm,bh1750 compatible"
    assert "bh1750_init" in body, "missing bh1750_init"
    assert "bh1750_read" in body, "missing bh1750_read"
    assert "bh1750_data" in body, "missing bh1750_data struct"
    assert "illuminance" in body, "missing illuminance field"


def test_bh1750_devicetree_overlay_has_rohm_compatible(synthetic_bh1750_dir):
    """Verify the devicetree overlay uses the rohm,bh1750 compatible."""
    boards_dir = synthetic_bh1750_dir / "app" / "boards"
    overlays = list(boards_dir.glob("*.overlay"))
    assert overlays, "No board overlay emitted"

    overlay_text = overlays[0].read_text(encoding="utf-8")
    assert "rohm,bh1750" in overlay_text, f"Overlay {overlays[0].name} missing rohm,bh1750 compatible"
    assert "0x23" in overlay_text, "Overlay missing I2C address 0x23"


def test_bh1750_prj_conf_has_kconfig(synthetic_bh1750_dir):
    """Assert prj.conf contains CONFIG_BH1750=y."""
    prj = synthetic_bh1750_dir / "app" / "prj.conf"
    assert prj.is_file(), "prj.conf not found"

    body = prj.read_text(encoding="utf-8")
    assert "CONFIG_BH1750=y" in body, "Missing CONFIG_BH1750=y in prj.conf"


def test_bh1750_generated_c_syntax(synthetic_bh1750_dir):
    """Validate bh1750.c passes C syntax check."""
    if not (_has_cpp() or _has_clang_format()):
        pytest.skip("No C toolchain (cpp / clang-format) available")

    bh1750 = synthetic_bh1750_dir / "app" / "src" / "bh1750.c"
    assert bh1750.is_file(), "bh1750.c not found"

    tool, ok, msg = _validate_c_syntax(bh1750)
    assert ok, f"bh1750.c failed {tool}: {msg}"
