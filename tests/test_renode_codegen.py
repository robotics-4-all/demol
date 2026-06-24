"""Syntax-level integrity tests for Renode code generation.

Validates the artifacts produced by ``demol.transformations.m2t_renode``:

1. The generator emits both ``device.repl`` and ``test_device.py`` at the
   project root for every ESP example.
2. The rendered ``.repl`` script contains the three required Renode
   directives — ``using sysbus``, ``mach create``, and
   ``machine LoadPlatformDescription`` — plus the ``sysbus LoadELF`` boot
   directive.
3. The rendered ``test_device.py`` driver imports ``pyrenode3`` and
   declares at least one ``def test_`` function.
4. The rendered ``test_device.py`` is syntactically valid Python
   (``ast.parse`` passes) so the ``pyrenode3``-based runtime can load it.

A Renode install is NOT required for these tests — they exercise the
generator end-to-end against the example ``.dev`` models and inspect the
emitted text only. The runtime suite that actually spawns the Renode
binary lives in ``test_renode_runtime.py``.
"""

from __future__ import annotations

import ast
import re
import warnings
from pathlib import Path

import pytest

from demol.lang import get_device_mm
from demol.transformations.m2t_renode import m2t_renode


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples" / "esp"


# Five representative ESP examples. The set covers both board families
# exercised by the Renode generator: WemosD1Mini (``wemos_*``) and
# esp32_devkitc (``esp_*``). ``wemos_dht11`` and ``wemos_pir`` are
# referenced in the multi-backend evolution plan but do not yet exist
# under ``examples/esp/``; the parametrize set therefore falls back to
# the five examples that are present.
ESP_EXAMPLES = [
    "wemos_bme680.dev",
    "wemos_button.dev",
    "wemos_srf05.dev",
    "esp_bme680.dev",
    "esp_iot_device.dev",
]


pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


@pytest.fixture(scope="module")
def renode_codegen_device_mm():
    """Dedicated device metamodel with semantics skipped.

    A separate metamodel isolates this module from the session-scoped
    ``device_mm`` fixture in ``conftest.py`` and from textX's global
    model repository, where model-processor errors on referenced
    ``.hwd`` sub-models could otherwise leak across tests. Semantic
    validation is irrelevant for the codegen path: the generator walks
    the parsed model structure and emits text.
    """
    return get_device_mm(skip_semantics=True)


@pytest.fixture(scope="module")
def renode_outputs(renode_codegen_device_mm, tmp_path_factory):
    """Generate Renode artifacts for every example once per test module.

    Returns a ``dict[example_filename -> output_dir]``. Generation is
    hoisted into a module-scoped fixture so the per-test parametrize
    iteration is cheap (we only need the file existence / text content
    on each test).
    """
    out_root = tmp_path_factory.mktemp("renode_codegen")
    outputs: dict[str, Path] = {}
    for example in ESP_EXAMPLES:
        model = renode_codegen_device_mm.model_from_file(
            str(EXAMPLES_DIR / example)
        )
        out_dir = out_root / example
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            m2t_renode(model, output_dir=str(out_dir))
        outputs[example] = out_dir
    return outputs


def _example_ids() -> list:
    return [Path(ex).stem for ex in ESP_EXAMPLES]


# ---------------------------------------------------------------------
# File-existence / tree-layout checks
# ---------------------------------------------------------------------


@pytest.mark.parametrize("example", ESP_EXAMPLES, ids=_example_ids())
def test_repl_and_test_script_files_exist(renode_outputs, example):
    """Generator must emit ``device.repl`` and ``test_device.py``.

    Both files are expected at the project root (mirrors the Wokwi
    project layout — the Renode simulator's ``include`` resolves
    relative paths from the script's directory).
    """
    out_dir = renode_outputs[example]
    assert (out_dir / "device.repl").is_file(), (
        f"missing device.repl for {example}"
    )
    assert (out_dir / "test_device.py").is_file(), (
        f"missing test_device.py for {example}"
    )


# ---------------------------------------------------------------------
# .repl content checks
# ---------------------------------------------------------------------


@pytest.mark.parametrize("example", ESP_EXAMPLES, ids=_example_ids())
def test_repl_starts_with_using_sysbus(renode_outputs, example):
    """``device.repl`` must declare the ``sysbus`` bus.

    Renode's ``machine LoadPlatformDescription`` semantics require
    the script to start with ``using sysbus`` (or an equivalent
    ``using`` directive for a non-sysbus bus).
    """
    repl = (renode_outputs[example] / "device.repl").read_text()
    assert "using sysbus" in repl, (
        f"device.repl for {example} missing required 'using sysbus' header"
    )


@pytest.mark.parametrize("example", ESP_EXAMPLES, ids=_example_ids())
def test_repl_has_mach_create_directive(renode_outputs, example):
    """``device.repl`` must contain a ``mach create`` directive.

    Without ``mach create`` the simulator has no machine to load the
    platform description into, and the script is a no-op.
    """
    repl = (renode_outputs[example] / "device.repl").read_text()
    assert "mach create" in repl, (
        f"device.repl for {example} missing required 'mach create' directive"
    )


@pytest.mark.parametrize("example", ESP_EXAMPLES, ids=_example_ids())
def test_repl_has_load_platform_description_directive(renode_outputs, example):
    """``device.repl`` must contain ``LoadPlatformDescription``.

    The platform description is what binds the simulated machine to
    a specific board (e.g. ``wemosd1mini`` / ``esp32_devkitc``). A
    REPL without this directive would not load any peripherals.
    """
    repl = (renode_outputs[example] / "device.repl").read_text()
    assert "LoadPlatformDescription" in repl, (
        f"device.repl for {example} missing required "
        "'LoadPlatformDescription' directive"
    )


@pytest.mark.parametrize("example", ESP_EXAMPLES, ids=_example_ids())
def test_repl_loads_firmware_elf(renode_outputs, example):
    """``device.repl`` must contain a ``sysbus LoadELF`` directive.

    The Renode script is meant to load a pre-built firmware ELF so
    the simulated board boots into the application. The template
    falls back to ``/tmp/firmware.elf`` when no ``--elf-path`` is
    passed; either way the directive is required.
    """
    repl = (renode_outputs[example] / "device.repl").read_text()
    assert "sysbus LoadELF" in repl, (
        f"device.repl for {example} missing required 'sysbus LoadELF' directive"
    )


# ---------------------------------------------------------------------
# test_device.py content checks
# ---------------------------------------------------------------------


@pytest.mark.parametrize("example", ESP_EXAMPLES, ids=_example_ids())
def test_test_script_imports_pyrenode3(renode_outputs, example):
    """``test_device.py`` must import ``pyrenode3``.

    The test driver relies on ``pyrenode3.Antmicro`` to spawn Renode
    in-process and load the ``.repl`` script. Without the import the
    driver is a no-op.
    """
    body = (renode_outputs[example] / "test_device.py").read_text()
    assert "pyrenode3" in body, (
        f"test_device.py for {example} does not import pyrenode3"
    )


@pytest.mark.parametrize("example", ESP_EXAMPLES, ids=_example_ids())
def test_test_script_has_at_least_one_test_function(renode_outputs, example):
    """``test_device.py`` must declare at least one ``def test_`` function.

    A driver with no test function is a runtime failure — pytest would
    report "no tests ran" once the script is loaded.
    """
    body = (renode_outputs[example] / "test_device.py").read_text()
    assert re.search(r"^def test_", body, re.MULTILINE), (
        f"test_device.py for {example} has no 'def test_' function"
    )


@pytest.mark.parametrize("example", ESP_EXAMPLES, ids=_example_ids())
def test_test_script_is_syntactically_valid_python(renode_outputs, example):
    """``test_device.py`` must parse cleanly as Python.

    The driver is loaded by ``pyrenode3`` / pytest at runtime, so a
    syntax error is a hard failure. We use ``ast.parse`` (no execution)
    so the check is pure-stdlib and does not require ``pyrenode3`` to
    be installed in the generator host environment.
    """
    test_script_path = renode_outputs[example] / "test_device.py"
    body = test_script_path.read_text()
    try:
        ast.parse(body, filename=str(test_script_path))
    except SyntaxError as exc:
        pytest.fail(
            f"test_device.py for {example} is not valid Python: {exc}"
        )


# ---------------------------------------------------------------------
# Cross-artifact checks
# ---------------------------------------------------------------------


@pytest.mark.parametrize("example", ESP_EXAMPLES, ids=_example_ids())
def test_test_script_references_the_generated_repl(renode_outputs, example):
    """``test_device.py`` must load the generated ``device.repl``.

    The driver calls ``ant.load_repl("device.repl")``; if it
    references a different filename the runtime cannot find the
    platform description. This guards against template drift where
    the REPL and the test script get out of sync.
    """
    body = (renode_outputs[example] / "test_device.py").read_text()
    assert "load_repl" in body, (
        f"test_device.py for {example} does not call load_repl"
    )
    assert "device.repl" in body, (
        f"test_device.py for {example} does not reference device.repl"
    )


def test_examples_directory_not_empty():
    """Sanity check: parametrize set must be non-empty.

    With an empty ``ESP_EXAMPLES`` the parametrized tests would
    silently pass; the floor guard keeps the suite honest.
    """
    assert ESP_EXAMPLES, (
        f"No ESP examples found under {EXAMPLES_DIR}; "
        "parametrized codegen tests would silently pass."
    )
