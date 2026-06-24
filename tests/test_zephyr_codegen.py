"""Syntax-level integrity tests for Zephyr code generation.

Verifies the Zephyr backend produces a complete app/ tree, that every
emitted .c file passes a C syntax check (cpp -fsyntax-only with local
Zephyr stub headers, or clang-format as a fallback), and that the
expected driver API symbols appear. A Zephyr SDK install is NOT
required.
"""

import shutil
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from demol.transformations.m2t_zephyr import m2t_zephyr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ESP_EXAMPLES_DIR = PROJECT_ROOT / "examples" / "esp"
ZEPHYR_STUBS_DIR = PROJECT_ROOT / "tests" / "fixtures" / "zephyr_stubs"
ESP_EXAMPLES = sorted(ESP_EXAMPLES_DIR.glob("*.dev"))

SYNTHETIC_BME680_MODEL = dedent("""\
    DEVICE SyntheticBme680 WITH description="bme680 codegen test", author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";
    """)


def _has_cpp() -> bool:
    return shutil.which("cpp") is not None


def _has_clang_format() -> bool:
    return shutil.which("clang-format") is not None


def _validate_c_syntax(c_file: Path) -> tuple:
    """Validate C syntax for one generated .c file.

    Returns ``(tool_name, ok, message)``. Prefers ``cpp -fsyntax-only``
    with the local Zephyr stub headers; falls back to ``clang-format``
    when cpp is missing. A failure here is almost always a template
    regression — the generated source is textually plausible (passes
    substring checks) but the C parser rejects it.
    """
    if _has_cpp() and ZEPHYR_STUBS_DIR.is_dir():
        cmd = ["cpp", "-fsyntax-only", f"-I{ZEPHYR_STUBS_DIR}", str(c_file)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return ("cpp -fsyntax-only", True, "")
        return (
            "cpp -fsyntax-only",
            False,
            f"{proc.stderr.strip() or proc.stdout.strip()}",
        )
    if _has_clang_format():
        # clang-format is a tolerant lexer: a parse error in the input
        # makes the command exit non-zero. We tolerate formatting-only
        # diffs by not passing --Werror.
        cmd = ["clang-format", str(c_file)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return ("clang-format", True, "")
        return (
            "clang-format",
            False,
            f"clang-format failed to lex {c_file.name}: " f"{proc.stderr.strip()[:200]}",
        )
    return ("", False, "no C toolchain available")


def _example_ids() -> list:
    return [p.stem for p in ESP_EXAMPLES]


@pytest.fixture(scope="module")
def synthetic_bme680_dir(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_synthetic_bme680")
    model = device_mm.model_from_str(SYNTHETIC_BME680_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


@pytest.mark.parametrize(
    "example_path",
    ESP_EXAMPLES,
    ids=_example_ids(),
)
def test_generated_zephyr_tree_layout(device_mm, tmp_path, example_path):
    model = device_mm.model_from_file(str(example_path))
    output_dir = tmp_path / example_path.stem
    m2t_zephyr(model, output_dir=str(output_dir))

    app_dir = output_dir / "app"
    assert app_dir.is_dir(), f"Missing app/ for {example_path.name}"

    assert (app_dir / "CMakeLists.txt").is_file(), "Missing app/CMakeLists.txt"
    assert (app_dir / "prj.conf").is_file(), "Missing app/prj.conf"
    assert (app_dir / "src" / "main.c").is_file(), "Missing app/src/main.c"

    overlays = list((app_dir / "boards").glob("*.overlay"))
    assert overlays, f"No board overlay emitted for {example_path.name}"


@pytest.mark.parametrize(
    "example_path",
    ESP_EXAMPLES,
    ids=_example_ids(),
)
def test_generated_c_passes_syntax_check(device_mm, tmp_path, example_path):
    if not (_has_cpp() or _has_clang_format()):
        pytest.skip("No C toolchain (cpp / clang-format) available")

    model = device_mm.model_from_file(str(example_path))
    output_dir = tmp_path / example_path.stem
    m2t_zephyr(model, output_dir=str(output_dir))

    c_files = sorted((output_dir / "app" / "src").glob("*.c"))
    assert c_files, f"No .c files generated for {example_path.name}"

    failures = []
    for c_file in c_files:
        tool, ok, msg = _validate_c_syntax(c_file)
        if not ok:
            failures.append(f"{c_file.name} ({tool}): {msg}")

    assert not failures, f"Generated C from {example_path.name} failed syntax check:\n  " + "\n  ".join(failures)


@pytest.mark.parametrize(
    "example_path",
    ESP_EXAMPLES,
    ids=_example_ids(),
)
def test_bme680_driver_uses_zephyr_sensor_api(device_mm, tmp_path, example_path):
    model = device_mm.model_from_file(str(example_path))
    output_dir = tmp_path / example_path.stem
    m2t_zephyr(model, output_dir=str(output_dir))

    bme680 = output_dir / "app" / "src" / "bme680.c"
    if not bme680.is_file():
        pytest.skip(f"{example_path.name} has no bme680.c (different peripheral set)")

    body = bme680.read_text(encoding="utf-8")
    assert "sensor_sample_fetch" in body, f"{example_path.name}: bme680.c missing sensor_sample_fetch"
    assert "DEVICE_DT_GET" in body, f"{example_path.name}: bme680.c missing DEVICE_DT_GET"


def test_synthetic_bme680_driver_emits_sensor_api(synthetic_bme680_dir):
    bme680 = synthetic_bme680_dir / "app" / "src" / "bme680.c"
    assert bme680.is_file(), "Synthetic bme680 model did not emit app/src/bme680.c"
    body = bme680.read_text(encoding="utf-8")
    assert "sensor_sample_fetch" in body
    assert "DEVICE_DT_GET" in body
    prj = (synthetic_bme680_dir / "app" / "prj.conf").read_text(encoding="utf-8")
    assert "CONFIG_BME680=y" in prj


def test_trigger_echo_macro_is_emitted(device_mm, tmp_path):
    # None of the ESP examples under examples/esp/ currently use HCSR04
    # (only HCSR04P, which has no Zephyr template), so we build the
    # model inline. The shared trigger_echo_init_<trig>_<echo> function
    # comes from demol/templates/zephyr/_macros.j2.
    model_str = dedent("""\
        DEVICE TriggerEcho WITH description="trigger-echo codegen test", author="demol-tests";

        NETWORK[WiFi] WITH ssid="test", password="test";
        BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

        USE WemosD1Mini;
        USE HCSR04[Range];

        CONNECT Range WITH
            POWER GND -- gnd, VCC -- power_5v
            DATA gpio[mode="output"] trigger -- d3, gpio[mode="input"] echo -- d4
            @ "test.distance";
        """)
    model = device_mm.model_from_str(model_str)
    out = tmp_path / "trigger_echo"
    m2t_zephyr(model, output_dir=str(out))

    hcsr04 = out / "app" / "src" / "hcsr04.c"
    assert hcsr04.is_file(), "hcsr04.c was not generated for HCSR04 model"
    body = hcsr04.read_text(encoding="utf-8")
    assert "trigger_echo_init" in body, "trigger_echo_init macro not emitted"


def test_examples_directory_not_empty():
    assert ESP_EXAMPLES, (
        f"No .dev examples found under {ESP_EXAMPLES_DIR}; " "parametrized syntax test would silently pass."
    )
