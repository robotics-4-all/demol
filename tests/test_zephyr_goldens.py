"""Golden-file snapshot tests for Zephyr code generation.

Uses [syrupy](https://syrupy.readthedocs.io/) to compare the generated
Zephyr application against committed snapshots. The generator output
is fully deterministic, so any drift indicates a template, grammar, or
generator regression that needs a deliberate review.

The snapshots are stored under ``tests/__snapshots__/`` per syrupy's
default layout. The ``tests/goldens/zephyr/`` directory is the
logical group used in PR descriptions; the actual ``.ambr`` files
live in ``__snapshots__/``.

Initial run (creates the goldens):

    pytest tests/test_zephyr_goldens.py -v --snapshot-update

Subsequent runs (CI):

    pytest tests/test_zephyr_goldens.py -v

CI must never pass ``--snapshot-update``.
"""

from pathlib import Path

import pytest

from demol.transformations.m2t_zephyr import m2t_zephyr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ESP_EXAMPLES_DIR = PROJECT_ROOT / "examples" / "esp"
ESP_EXAMPLES = sorted(ESP_EXAMPLES_DIR.glob("*.dev"))


def _collect_artifacts(output_dir: Path) -> dict:
    """Collect every generated artifact into a single snapshot dict.

    The dict is keyed by a path relative to the app/ root so the
    snapshot diff is easy to navigate. Files under ``app/dts/`` and
    any ``.gitkeep`` placeholder are excluded to keep the snapshot
    focused on codegen output that humans care about.
    """
    app_dir = output_dir / "app"
    if not app_dir.is_dir():
        return {}

    files = {}
    for path in sorted(app_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name == ".gitkeep":
            continue
        if ".git" in path.parts:
            continue
        rel = path.relative_to(app_dir).as_posix()
        files[rel] = path.read_text(encoding="utf-8")
    return files


@pytest.mark.parametrize(
    "example_path",
    ESP_EXAMPLES,
    ids=[p.stem for p in ESP_EXAMPLES],
)
def test_zephyr_codegen_golden(device_mm, tmp_path, snapshot, example_path):
    model = device_mm.model_from_file(str(example_path))
    output_dir = tmp_path / example_path.stem
    m2t_zephyr(model, output_dir=str(output_dir))

    artifacts = _collect_artifacts(output_dir)
    assert artifacts, f"No artifacts generated for {example_path.name}"
    assert artifacts == snapshot(name=example_path.stem)


def test_examples_directory_not_empty():
    assert ESP_EXAMPLES, (
        f"No .dev examples found under {ESP_EXAMPLES_DIR}; "
        "golden snapshots would silently pass."
    )
