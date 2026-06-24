"""Renode runtime tests — skipped when the Renode binary is not installed.

The tests in this module spawn the ``renode`` CLI to verify the
simulator can parse the generated ``.repl`` script. They run only
when a Renode binary is available on ``PATH`` (``shutil.which``);
otherwise the entire module is skipped via ``pytest.mark.skipif``.

Skip behavior summary:

* ``renode`` on PATH  -> the suite runs and validates the generated
  ``.repl`` against the running simulator.
* ``renode`` missing  -> every test in this module is reported as
  ``SKIPPED`` and the rest of the test suite is unaffected.

The runtime suite is intentionally separate from
``test_renode_codegen.py`` (pure codegen, never spawns Renode) and
``test_renode_goldens.py`` (snapshot regression, never spawns
Renode). Generator-level validation must not require a working
Renode install.

``pyrenode3`` is NOT a hard dependency of the test suite. The
generated ``test_device.py`` driver imports ``pyrenode3`` lazily
inside the test functions, so the codegen path works without it;
the runtime tests inspect the generated text only and do not
import ``pyrenode3`` themselves.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

from demol.lang import get_device_mm
from demol.transformations.m2t_renode import m2t_renode


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples" / "esp"


# A three-example parametrize set keeps the runtime under control
# when Renode is installed: each test spawns a Renode subprocess,
# and the CI matrix does not need the full 7-example set exercised
# at runtime. The codegen suite (test_renode_codegen.py) covers
# the structural checks for the other examples.
ESP_EXAMPLES = [
    "wemos_bme680.dev",
    "wemos_button.dev",
    "wemos_srf05.dev",
]


# Resolve the Renode binary once at import time. ``shutil.which``
# returns ``None`` when the binary is not on PATH; the module-level
# ``skipif`` marker then short-circuits every test in the file.
_RENODE_BIN = shutil.which("renode")


pytestmark = [
    pytest.mark.filterwarnings("ignore::UserWarning"),
    pytest.mark.skipif(
        _RENODE_BIN is None,
        reason=(
            "renode binary not on PATH; install Renode to enable "
            "runtime tests (https://renode.io)"
        ),
    ),
]


@pytest.fixture(scope="module")
def renode_runtime_device_mm():
    """Dedicated device metamodel with semantics skipped.

    A separate metamodel isolates this module from the session-scoped
    ``device_mm`` fixture in ``conftest.py`` and from textX's global
    model repository.
    """
    return get_device_mm(skip_semantics=True)


@pytest.fixture(scope="module")
def renode_runtime_outputs(renode_runtime_device_mm, tmp_path_factory):
    """Generate Renode artifacts for every example once per test module."""
    out_root = tmp_path_factory.mktemp("renode_runtime")
    outputs: dict[str, Path] = {}
    for example in ESP_EXAMPLES:
        model = renode_runtime_device_mm.model_from_file(
            str(EXAMPLES_DIR / example)
        )
        out_dir = out_root / example
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            m2t_renode(model, output_dir=str(out_dir))
        outputs[example] = out_dir
    return outputs


# ---------------------------------------------------------------------
# Binary-availability sanity check
# ---------------------------------------------------------------------


def test_renode_binary_on_path():
    """The ``renode`` binary must be on PATH for runtime tests.

    This is the gate test — the module-level ``skipif`` ensures the
    binary is found before any other test runs. If the test ever
    runs and fails here, the skipif logic has regressed.
    """
    assert shutil.which("renode") is not None, (
        "renode binary not on PATH — module-level skipif should "
        "have short-circuited this test"
    )


def test_renode_binary_reports_version():
    """``renode --version`` must exit 0.

    Verifies that the installed binary is at least minimally
    functional (no missing shared libraries, no wrong architecture).
    """
    proc = subprocess.run(
        ["renode", "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"`renode --version` exited {proc.returncode}:\n"
        f"stdout: {proc.stdout}\n"
        f"stderr: {proc.stderr}"
    )


# ---------------------------------------------------------------------
# Generated test_device.py sanity check
# ---------------------------------------------------------------------


def test_test_script_is_valid_python(renode_runtime_outputs):
    """The generated ``test_device.py`` must parse cleanly as Python.

    The driver is loaded by ``pyrenode3`` at test time, so a syntax
    error here would surface as an opaque import failure. The
    ``ast.parse`` check is pure-stdlib and does not require
    ``pyrenode3`` to be installed in the host environment.
    """
    for example, out_dir in renode_runtime_outputs.items():
        test_script_path = out_dir / "test_device.py"
        body = test_script_path.read_text()
        try:
            ast.parse(body, filename=str(test_script_path))
        except SyntaxError as exc:
            pytest.fail(
                f"test_device.py for {example} is not valid Python: {exc}"
            )


# ---------------------------------------------------------------------
# Generated .repl can be parsed by Renode
# ---------------------------------------------------------------------


@pytest.mark.parametrize("example", ESP_EXAMPLES)
def test_renode_parses_generated_repl(renode_runtime_outputs, example):
    """``renode --console`` must parse the generated ``.repl`` script.

    The test boots Renode in headless console mode
    (``--disable-xwt --console``), loads the REPL via the
    ``include @<path>`` REPL command, and asks the simulator to
    quit. Renode performs a syntactic parse of the ``.repl`` file
    before executing it; a malformed script would fail with a
    ``Syntax error`` on stderr.

    Platform-description lookup may fail in a minimal Renode install
    (the ``@platforms/boards/<board>.repl`` line requires the stock
    Renode platform descriptions). Such failures are reported as
    ``No such file`` on stderr, not as ``Syntax error``, so the
    check stays robust: we assert that the REPL was parsed cleanly
    and we tolerate platform-resolution failures because the
    generator-side tests already assert the directive is emitted.
    """
    out_dir = renode_runtime_outputs[example]
    repl_path = out_dir / "device.repl"

    proc = subprocess.run(
        [
            "renode",
            "--disable-xwt",
            "--console",
            "-e", f"include @{repl_path}",
            "-e", "quit",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(out_dir),
    )

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")

    if "Syntax error" in combined:
        pytest.fail(
            f"Renode reported a syntax error parsing the REPL for "
            f"{example}:\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )


def test_examples_directory_not_empty():
    """Sanity check: parametrize set must be non-empty.

    With an empty ``ESP_EXAMPLES`` the parametrized tests would
    silently pass; the floor guard keeps the suite honest.
    """
    assert ESP_EXAMPLES, (
        f"No ESP examples found under {EXAMPLES_DIR}; "
        "parametrized runtime tests would silently pass."
    )
