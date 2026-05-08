"""Syntax-level integrity tests for RPi code generation.

For every example .dev model in examples/rpi/, generate the RPi Python
code and verify every emitted .py file with both ast.parse and py_compile.
This catches template regressions that produce textually-plausible but
unparseable / uncompilable Python — something the substring-based
assertion suite in test_rpi_transformation.py cannot detect.

py_compile is stricter than ast.parse: it byte-compiles the module,
exercising the full Python compiler (including some import-time error
classes) rather than only the parser.
"""

import ast
import py_compile
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
    compile_errors = []
    for py_file in py_files:
        source = py_file.read_text()
        try:
            ast.parse(source, filename=str(py_file))
        except SyntaxError as exc:
            syntax_errors.append(f"{py_file.relative_to(output_dir)}:{exc.lineno}: {exc.msg}")
            continue
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            compile_errors.append(f"{py_file.relative_to(output_dir)}: {exc.msg.strip()}")

    failures = []
    if syntax_errors:
        failures.append("AST parse errors:\n  " + "\n  ".join(syntax_errors))
    if compile_errors:
        failures.append("py_compile errors:\n  " + "\n  ".join(compile_errors))
    assert not failures, f"Generated Python from {example_path.name} failed checks:\n" + "\n".join(failures)


def test_examples_directory_not_empty():
    assert RPI_EXAMPLES, (
        f"No .dev examples found under {RPI_EXAMPLES_DIR}; " "parametrized syntax test would silently pass."
    )
