"""Renode golden-file snapshot tests.

Renders ``device.repl`` and ``test_device.py`` for each ESP example
and asserts byte-for-byte stability against committed syrupy
snapshots. Pure Python: no Renode CLI, no account/token, no network.

* Snapshots are committed to ``tests/__snapshots__/``.
* Update with ``pytest tests/test_renode_goldens.py --snapshot-update``.

The five-example parametrize set covers both board families the
Renode generator supports (WemosD1Mini via ``wemos_*`` and
esp32_devkitc via ``esp_*``). Snapshotting a stable, well-defined
subset keeps the diff readable when generator changes are
intentional; the full 7-example set is exercised by
``test_renode_codegen.py`` for non-snapshot structural checks.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from demol.lang import get_device_mm
from demol.transformations.m2t_renode import m2t_renode

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples" / "esp"


_ESP_EXAMPLES = [
    "wemos_bme680.dev",
    "wemos_button.dev",
    "wemos_srf05.dev",
    "esp_bme680.dev",
    "esp_iot_device.dev",
]


pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


@pytest.fixture(scope="module")
def renode_goldens_device_mm():
    """Dedicated device metamodel with semantics skipped.

    A separate metamodel isolates this module from the session-scoped
    ``device_mm`` fixture in ``conftest.py`` and from textX's global
    model repository, where model-processor errors on referenced
    ``.hwd`` sub-models would otherwise leak across the test session.
    """
    return get_device_mm(skip_semantics=True)


@pytest.fixture(scope="module")
def renode_artifacts(renode_goldens_device_mm, tmp_path_factory):
    """Generate Renode artifacts for every example once per test module.

    Returns a ``dict[example_filename -> {"device_repl": str,
    "test_device_py": str}]``. The artifacts are generated once and
    cached at module scope so the per-test parametrize iteration is
    cheap (each test only re-reads the in-memory text and compares it
    against the committed syrupy snapshot).
    """
    out_root = tmp_path_factory.mktemp("renode_goldens")
    artifacts: dict[str, dict[str, str]] = {}
    for example in _ESP_EXAMPLES:
        model = renode_goldens_device_mm.model_from_file(str(EXAMPLES_DIR / example))
        out_dir = out_root / example
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            m2t_renode(model, output_dir=str(out_dir))
        artifacts[example] = {
            "device_repl": (out_dir / "device.repl").read_text(),
            "test_device_py": (out_dir / "test_device.py").read_text(),
        }
    return artifacts


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_device_repl_golden(renode_artifacts, snapshot, example):
    """``device.repl`` for each example must match the committed snapshot."""
    assert renode_artifacts[example]["device_repl"] == snapshot


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_test_device_py_golden(renode_artifacts, snapshot, example):
    """``test_device.py`` for each example must match the committed snapshot."""
    assert renode_artifacts[example]["test_device_py"] == snapshot


def test_examples_directory_not_empty():
    """Sanity check: parametrize set must be non-empty.

    With an empty ``_ESP_EXAMPLES`` the parametrized tests would
    silently pass; the floor guard keeps the suite honest.
    """
    assert _ESP_EXAMPLES, f"No ESP examples found under {EXAMPLES_DIR}; " "golden snapshots would silently pass."
