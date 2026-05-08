"""Syntax-level integrity tests for RPi code generation.

For every example .dev model in examples/rpi/, generate the RPi Python
code and run ast.parse on every emitted .py file. This catches template
regressions that produce textually-plausible but unparseable Python —
something the substring-based assertion suite in test_rpi_transformation.py
cannot detect.
"""

import ast
from pathlib import Path

import pytest

from demol.transformations.m2t_rpi import m2t_rpi

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RPI_EXAMPLES_DIR = PROJECT_ROOT / "examples" / "rpi"
RPI_EXAMPLES = sorted(RPI_EXAMPLES_DIR.glob("*.dev"))


@pytest.mark.parametrize(
    "example_path",
    RPI_EXAMPLES,
    ids=[p.stem for p in RPI_EXAMPLES],
)
def test_generated_python_parses(device_mm, tmp_path, example_path):
    model = device_mm.model_from_file(str(example_path))
    output_dir = tmp_path / example_path.stem
    m2t_rpi(model, output_dir=str(output_dir))

    py_files = sorted(output_dir.rglob("*.py"))
    assert py_files, f"No Python files generated for {example_path.name}"

    syntax_errors = []
    for py_file in py_files:
        source = py_file.read_text()
        try:
            ast.parse(source, filename=str(py_file))
        except SyntaxError as exc:
            syntax_errors.append(f"{py_file.relative_to(output_dir)}:{exc.lineno}: {exc.msg}")

    assert not syntax_errors, f"Generated Python from {example_path.name} has syntax errors:\n  " + "\n  ".join(
        syntax_errors
    )


def test_examples_directory_not_empty():
    assert RPI_EXAMPLES, (
        f"No .dev examples found under {RPI_EXAMPLES_DIR}; " "parametrized syntax test would silently pass."
    )
