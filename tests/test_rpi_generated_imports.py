"""L1: the generated RPi tree must be importable as flat, script-launched code.

Generation-only tests (ast.parse/py_compile) cannot catch a broken module
graph. These tests actually import every generated module in a subprocess,
stubbing hardware-only third-party libraries on demand.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = sorted(
    (Path(__file__).resolve().parents[1] / "examples" / "rpi").glob("*.dev")
)

PROBE = r"""
import importlib
import sys
import types
from unittest.mock import MagicMock


class _StubModule(types.ModuleType):
    def __getattr__(self, item):
        if item.startswith("__"):
            raise AttributeError(item)
        value = MagicMock(name=f"{self.__name__}.{item}")
        setattr(self, item, value)
        return value


def _install(full_name):
    parts = full_name.split(".")
    for index in range(1, len(parts) + 1):
        current = ".".join(parts[:index])
        if current in sys.modules:
            continue
        module = _StubModule(current)
        module.__path__ = []
        sys.modules[current] = module
        if index > 1:
            setattr(sys.modules[".".join(parts[: index - 1])], parts[index - 1], module)


root = sys.argv[1]
targets = sys.argv[2:]
target_roots = {name.split(".")[0] for name in targets}
sys.path.insert(0, root)

stubbed = set()
for _attempt in range(300):
    try:
        for name in targets:
            importlib.import_module(name)
    except ModuleNotFoundError as exc:
        missing = exc.name or ""
        root_name = missing.split(".")[0]
        if not missing or root_name in target_roots or missing in stubbed:
            raise
        _install(missing)
        stubbed.add(missing)
        continue
    print("IMPORT-OK")
    raise SystemExit(0)

raise SystemExit("import probe did not converge")
"""


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.stem)
def test_generated_tree_is_flat_and_importable(device_mm, tmp_path, example):
    from demol.transformations.m2t_rpi import m2t_rpi

    out_dir = tmp_path / example.stem
    model = device_mm.model_from_file(str(example))
    m2t_rpi(model, output_dir=str(out_dir))

    assert (out_dir / "peripheral.py").is_file(), "peripheral.py was not generated"

    generated = sorted(out_dir.glob("*.py"))
    assert generated
    for path in generated:
        text = path.read_text(encoding="utf-8")
        assert "from ." not in text, (
            f"{path.name} uses a package-relative import in a flat layout"
        )

    probe = tmp_path / "_import_probe.py"
    probe.write_text(PROBE, encoding="utf-8")
    targets = [path.stem for path in generated]
    result = subprocess.run(
        [sys.executable, str(probe), str(out_dir), *targets],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")


PI4_BASE_MODEL = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "rpi"
    / "rpi_battery_power_analysis.dev"
)


def _run_import_probe(out_dir, tmp_path):
    probe = tmp_path / "_import_probe.py"
    probe.write_text(PROBE, encoding="utf-8")
    targets = [path.stem for path in sorted(out_dir.glob("*.py"))]
    return subprocess.run(
        [sys.executable, str(probe), str(out_dir), *targets],
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.mark.parametrize("board", ["RaspberryPi_3B", "RaspberryPi_4B_4GB"])
def test_pi3_and_pi4_board_output_is_importable(device_mm, tmp_path, board):
    """The stated targets are Pi 3 and Pi 4; the example corpus is mostly Pi 5."""
    from demol.transformations.m2t_rpi import m2t_rpi

    source = PI4_BASE_MODEL.read_text(encoding="utf-8")
    assert "RaspberryPi_4B_4GB" in source
    model_path = tmp_path / f"{board}.dev"
    model_path.write_text(
        source.replace("RaspberryPi_4B_4GB", board), encoding="utf-8"
    )

    out_dir = tmp_path / f"out_{board}"
    m2t_rpi(device_mm.model_from_file(str(model_path)), output_dir=str(out_dir))

    assert (out_dir / "peripheral.py").is_file()
    result = _run_import_probe(out_dir, tmp_path)
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")


TEMPLATE_DIR = (
    Path(__file__).resolve().parents[1] / "demol" / "templates" / "rpi"
)


def test_python_templates_escape_interpolated_string_literals():
    """Model-controlled strings must not be pasted raw between quotes."""
    offenders = [
        path.name
        for path in TEMPLATE_DIR.glob("*.py.j2")
        if '"{{' in path.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders
