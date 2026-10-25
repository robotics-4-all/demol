"""Regression test: every DeMoL example model must parse cleanly.

Parametrises the test suite over every ``.dev`` file under ``examples/``
(the existing ``rpi/``, ``esp/``, ``smauto/`` directories plus the
multi-backend suite in ``multi/``) and asserts that each one builds
into a valid textX device model. The test catches:

* grammar regressions that surface only on real-world models (the
  inline-string tests in ``test_parser_robustness.py`` only cover
  the most common constructs);
* accidental edits to example files that introduce syntax / scoping
  errors;
* a missing or renamed example that breaks the regression gate.

The test is parse-only. It does not run the full semantic validator
on each model (some examples exercise intentionally-erroneous
constructs to document failure modes) and it does not invoke any
code generators. The companion ``test_cross_backend_integration.py``
file is the source of truth for the cross-backend codegen matrix.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_ROOT = PROJECT_ROOT / "examples"

# Directories that ship user-facing device-model examples. The
# ``multi/`` subdirectory is the new home for the cross-backend
# showcase suite (simple_sensor, actuator_switch, iot_mqtt).
_EXAMPLE_SUBDIRS: List[str] = ["rpi", "esp", "smauto", "multi"]


def _collect_example_models() -> List[Path]:
    """Return every ``.dev`` file under the example subdirectories.

    The list is sorted so the test parameter ids are stable across
    runs; the ``pytest -v`` output is then alphabetical and easy to
    diff between commits.
    """
    models: List[Path] = []
    for subdir in _EXAMPLE_SUBDIRS:
        directory = EXAMPLES_ROOT / subdir
        if not directory.is_dir():
            continue
        models.extend(sorted(directory.glob("*.dev")))
    return models


EXAMPLE_MODELS: List[Path] = _collect_example_models()


def _example_id(path: Path) -> str:
    """Stable test id: ``rpi/multi_periph`` or ``multi/simple_sensor``."""
    return f"{path.parent.name}/{path.stem}"


@pytest.mark.parametrize(
    "example_path",
    EXAMPLE_MODELS,
    ids=[_example_id(p) for p in EXAMPLE_MODELS],
)
def test_example_model_parses(device_mm, example_path):
    """Each shipped example must build a valid textX device model.

    The ``device_mm`` fixture is the session-scoped metamodel defined
    in ``tests/conftest.py``. We deliberately do not pass
    ``skip_semantics=True`` here — every example that ships in the
    gallery is expected to satisfy the default semantic rules; if one
    stops satisfying them, the example is the thing that changed.
    """
    model = device_mm.model_from_file(str(example_path))
    assert model is not None, f"model_from_file returned None for {example_path}"
    assert getattr(model, "metadata", None) is not None, f"{example_path} did not produce a device model with metadata"
    assert getattr(model.metadata, "name", None), f"{example_path} parsed but produced no device name"


def test_example_gallery_is_not_empty():
    """Guard against a silent example-discovery regression."""
    assert EXAMPLE_MODELS, "no .dev example models discovered under examples/; " f"checked subdirs: {_EXAMPLE_SUBDIRS}"


def test_example_gallery_includes_multi_suite():
    """The multi-backend showcase suite must be part of the gallery."""
    multi_dir = EXAMPLES_ROOT / "multi"
    assert multi_dir.is_dir(), f"missing examples/multi directory: {multi_dir}"
    multi_models = sorted(p.stem for p in multi_dir.glob("*.dev"))
    expected = {"simple_sensor", "actuator_switch", "iot_mqtt"}
    missing = expected - set(multi_models)
    assert not missing, f"examples/multi/ is missing the showcase files {sorted(missing)}; " f"found: {multi_models}"
