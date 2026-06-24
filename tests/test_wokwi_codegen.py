"""Wokwi code-generation tests.

Validates the artifacts produced by ``demol.transformations.m2t_wokwi`` against
the Wokwi diagram format. The tests are:

* Pure Python: no Wokwi CLI, no account/token, no network.
* Schema-driven: ``diagram.json`` must conform to ``tests/wokwi_schema.json``
  (a strict subset of the Wokwi diagram format).
* Parametrized over the five ESP examples under ``examples/esp/``.

For each example the suite asserts:

1. The generator emits ``diagram.json`` and ``wokwi.toml`` at the project root.
2. ``diagram.json`` is parseable JSON and contains the five required top-level
   fields (``version``, ``author``, ``editor``, ``parts``, ``connections``).
3. ``diagram.json`` validates against ``tests/wokwi_schema.json`` via the
   ``jsonschema`` library.
4. ``wokwi.toml`` is non-empty and contains the mandatory ``[wokwi]`` table.
5. ``connections`` reference part ids that actually exist in ``parts``.
6. All generated parts use a non-empty ``type`` string.
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


_REQUIRED_TOP_FIELDS = ("version", "author", "editor", "parts", "connections")


pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


@pytest.fixture(scope="session")
def wokwi_schema() -> dict:
    """Load and return the Wokwi diagram.json JSON Schema."""
    with SCHEMA_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="session")
def wokwi_device_mm():
    """Dedicated device metamodel with semantics skipped.

    The Wokwi backend walks the parsed model structure only, so semantic
    validation is irrelevant for these tests. A dedicated metamodel also
    isolates the test session from textX's global model repository, where
    model-processor errors on referenced ``.hwd`` sub-models would
    otherwise leak across tests.
    """
    return get_device_mm(skip_semantics=True)


@pytest.fixture(scope="session")
def wokwi_outputs(tmp_path_factory, wokwi_device_mm):
    """Generate Wokwi artifacts for every example once per test session.

    Returns a dict mapping example file name (e.g. ``"wemos_bme680.dev"``)
    to the output directory containing the generated files.
    """
    out_root = tmp_path_factory.mktemp("wokwi_codegen")
    outputs: dict[str, Path] = {}
    for example in _ESP_EXAMPLES:
        model_path = EXAMPLES_DIR / example
        model = wokwi_device_mm.model_from_file(str(model_path))
        out_dir = out_root / example
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            m2t_wokwi(model, output_dir=str(out_dir))
        outputs[example] = out_dir
    return outputs


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_and_toml_files_exist(wokwi_outputs, example):
    """Generator must emit diagram.json and wokwi.toml at the project root."""
    out_dir = wokwi_outputs[example]
    assert (out_dir / "diagram.json").is_file(), f"missing diagram.json for {example}"
    assert (out_dir / "wokwi.toml").is_file(), f"missing wokwi.toml for {example}"


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_is_valid_json(wokwi_outputs, example):
    """The emitted diagram.json must be parseable JSON."""
    diagram_path = wokwi_outputs[example] / "diagram.json"
    data = json.loads(diagram_path.read_text())
    assert isinstance(data, dict)


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_has_required_top_level_fields(wokwi_outputs, example):
    """All five required fields must be present at the top level."""
    diagram = json.loads((wokwi_outputs[example] / "diagram.json").read_text())
    for field in _REQUIRED_TOP_FIELDS:
        assert field in diagram, f"diagram.json for {example} missing required field '{field}'"


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_validates_against_wokwi_schema(wokwi_outputs, wokwi_schema, example):
    """The emitted diagram.json must conform to tests/wokwi_schema.json."""
    diagram = json.loads((wokwi_outputs[example] / "diagram.json").read_text())
    jsonschema.validate(instance=diagram, schema=wokwi_schema)


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_version_is_int_one(wokwi_outputs, example):
    """Wokwi diagram format version must be the integer 1."""
    diagram = json.loads((wokwi_outputs[example] / "diagram.json").read_text())
    assert diagram["version"] == 1
    assert isinstance(diagram["version"], int)


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_author_and_editor_are_strings(wokwi_outputs, example):
    """``author`` and ``editor`` must be non-empty strings."""
    diagram = json.loads((wokwi_outputs[example] / "diagram.json").read_text())
    assert isinstance(diagram["author"], str) and diagram["author"]
    assert isinstance(diagram["editor"], str) and diagram["editor"]


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_parts_have_unique_ids(wokwi_outputs, example):
    """Every entry in ``parts`` must have a unique ``id``."""
    diagram = json.loads((wokwi_outputs[example] / "diagram.json").read_text())
    ids = [p["id"] for p in diagram["parts"]]
    assert len(ids) == len(set(ids)), f"duplicate part ids in {example}: {ids}"


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_connections_reference_known_parts(wokwi_outputs, example):
    """Every connection endpoint must reference an id present in ``parts``."""
    diagram = json.loads((wokwi_outputs[example] / "diagram.json").read_text())
    known = {p["id"] for p in diagram["parts"]}
    for conn in diagram["connections"]:
        for endpoint in (conn[0], conn[1]):
            part_id, _, _pin = endpoint.partition(":")
            assert part_id in known, (
                f"connection endpoint '{endpoint}' in {example} " f"references unknown part id '{part_id}'"
            )


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_diagram_connections_are_4_tuples(wokwi_outputs, example):
    """Wokwi connections must be 4-element arrays: [from, to, color, wires]."""
    diagram = json.loads((wokwi_outputs[example] / "diagram.json").read_text())
    for conn in diagram["connections"]:
        assert isinstance(conn, list)
        assert len(conn) == 4, f"connection in {example} is not a 4-tuple: {conn!r}"


@pytest.mark.parametrize("example", _ESP_EXAMPLES)
def test_wokwi_toml_has_wokwi_section(wokwi_outputs, example):
    """wokwi.toml must contain the mandatory [wokwi] section header."""
    body = (wokwi_outputs[example] / "wokwi.toml").read_text()
    assert "[wokwi]" in body, f"wokwi.toml for {example} missing [wokwi] section"
    assert "version" in body


def test_wokwi_schema_is_valid_json_schema(wokwi_schema):
    """The schema document under tests/wokwi_schema.json must be well-formed."""
    jsonschema.Draft202012Validator.check_schema(wokwi_schema)
