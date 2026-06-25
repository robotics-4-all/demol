"""CI guard: fail if any golden snapshot directory is empty.

Each of the three golden directories (``tests/goldens/{zephyr,wokwi,renode}/``)
is expected to contain at least one ``.ambr`` syrupy snapshot file. If any
directory is empty, tests that depend on those snapshots will silently pass
with zero parametrized cases — a dangerous false negative.

This file is the floor guard. It must pass in CI before the golden tests run.
"""

from pathlib import Path

import pytest

GOLDENS_DIR = Path(__file__).resolve().parent / "goldens"
BACKEND_DIRS = [
    "zephyr",
    "wokwi",
    "renode",
]
SNAPSHOTS_DIR = Path(__file__).resolve().parent / "__snapshots__"
EXPECTED_SNAPSHOT_FILES = [
    "test_zephyr_goldens.ambr",
    "test_wokwi_goldens.ambr",
    "test_renode_goldens.ambr",
]


@pytest.mark.parametrize("backend", BACKEND_DIRS)
def test_golden_dir_has_ambr_file(backend: str) -> None:
    """Each golden backend directory must contain at least one .ambr file."""
    golden_dir = GOLDENS_DIR / backend
    assert golden_dir.is_dir(), (
        f"Golden directory {golden_dir} does not exist. "
        f"Run: pytest tests/test_{backend}_goldens.py --snapshot-update"
    )
    ambr_files = list(golden_dir.glob("*.ambr"))
    assert ambr_files, (
        f"No .ambr files found in {golden_dir}. "
        f"Run: pytest tests/test_{backend}_goldens.py --snapshot-update"
    )


@pytest.mark.parametrize("snapshot_file", EXPECTED_SNAPSHOT_FILES)
def test_snapshot_file_exists(snapshot_file: str) -> None:
    """Each expected syrupy .ambr file must exist under __snapshots__/."""
    path = SNAPSHOTS_DIR / snapshot_file
    assert path.is_file(), (
        f"Expected snapshot file {path} not found. "
        f"Run the corresponding golden test with --snapshot-update."
    )


def test_all_three_backends_have_snapshots() -> None:
    """At least three .ambr files (one per backend) must exist in __snapshots__/."""
    ambr_files = list(SNAPSHOTS_DIR.glob("*.ambr"))
    assert len(ambr_files) >= 3, (
        f"Expected at least 3 .ambr snapshot files in {SNAPSHOTS_DIR}, "
        f"found {len(ambr_files)}: {[f.name for f in ambr_files]}"
    )
