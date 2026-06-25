"""Wokwi golden-file snapshot tests.

Renders ``diagram.json`` and ``wokwi.toml`` for each ESP example and
asserts byte-for-byte stability against committed syrupy snapshots.

* Pure Python: no Wokwi CLI, no account/token, no network.
* Snapshots are committed to ``tests/__snapshots__/``.
* Update with ``pytest tests/test_wokwi_goldens.py --snapshot-update``.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import jsonschema
import pytest

from demol.lang import get_device_mm
from demol.transformations.m2t_wokwi import m2t_wokwi

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "tests" / "wokwi_schema.json"
EXAMPLES_DIR = REPO_ROOT / "examples" / "esp"


_ESP_EXAMPLES = [
    "esp_iot_device.dev",
    "wemos_a.dev",
    "wemos_bme680.dev",
    "wemos_button.dev",
    "wemos_srf05.dev",
]


pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


@pytest.fixture(scope="module")
def wokwi_schema() -> dict:
    with SCHEMA_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def wokwi_device_mm():
    """Dedicated device metamodel with semantics skipped.

    Isolates the goldens test module from the session-scoped ``device_mm``
    fixture and from textX's global model repository, where model-processor
    errors on referenced ``.hwd`` sub-models would otherwise leak across
    the test session.
    """
    return get_device_mm(skip_semantics=True)


@pytest.fixture(scope="module")
def wokwi_artifacts(wokwi_device_mm, tmp_path_factory):
    out_root = tmp_path_factory.mktemp("wokwi_goldens")
    artifacts: dict[str, dict[str, str]] = {}
    for example in _ESP_EXAMPLES:
        model = wokwi_device_mm.model_from_file(str(EXAMPLES_DIR / example))
        out_dir = out_root / example
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            m2t_wokwi(model, output_dir=str(out_dir))
        artifacts[example] = {
            "diagram_json": (out_dir / "diagram.json").read_text(),
            "wokwi_toml": (out_dir / "wokwi.toml").read_text(),
        }
    return artifacts


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_json_golden(wokwi_artifacts, snapshot, example):
    assert wokwi_artifacts[example]["diagram_json"] == snapshot


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_wokwi_toml_golden(wokwi_artifacts, snapshot, example):
    assert wokwi_artifacts[example]["wokwi_toml"] == snapshot


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_json_validates_against_schema(wokwi_artifacts, wokwi_schema, example):
    diagram = json.loads(wokwi_artifacts[example]["diagram_json"])
    jsonschema.validate(instance=diagram, schema=wokwi_schema)
