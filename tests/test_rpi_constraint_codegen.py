"""String-level emission tests for CONSTRAINT runtime codegen on the RPi target.

Covers the contract documented in ``docs/constraint-runtime-design.md`` Section 2:
- ``constraints.py`` runtime helper is emitted when the model declares constraints
- A model with no constraints produces NO ``constraints.py`` (backward compat)
- The module exposes ``check_constraints()`` and helper functions
  ``count(kind)``, ``sum_power(kind)``, ``avg_power(kind)``, ``max_power(kind)``
  that read from a thread-safe ``_registry`` dict
- Per-constraint MESSAGE strings are preserved in the emitted code
- Generation is deterministic: two runs produce byte-identical output
"""

import ast
import subprocess
from pathlib import Path

import pytest

from demol.transformations.m2t_rpi import RPiCodeGenerator


@pytest.fixture(scope="module")
def constraints_demo_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("rpi_constraints_demo")
    model = device_mm.model_from_file("examples/rpi/rpi_constraints_demo.dev")
    RPiCodeGenerator(model, out).generate()
    return out


@pytest.fixture(scope="module")
def multi_periph_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("rpi_multi_periph")
    model = device_mm.model_from_file("examples/rpi/multi_periph.dev")
    RPiCodeGenerator(model, out).generate()
    return out


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class TestConstraintsRuntimeEmission:
    def test_constraints_module_emitted(self, constraints_demo_out):
        """A model with CONSTRAINTs produces a constraints.py file."""
        assert (constraints_demo_out / "constraints.py").is_file()

    def test_constraints_module_is_valid_python(self, constraints_demo_out):
        """The generated file must be syntactically valid Python."""
        body = _read(constraints_demo_out / "constraints.py")
        ast.parse(body)

    def test_constraints_module_exports_check_function(self, constraints_demo_out):
        body = _read(constraints_demo_out / "constraints.py")
        assert "def check_constraints" in body
        # call site that the main loop uses
        assert "check_constraints()" in body

    def test_constraints_module_exposes_helper_functions(self, constraints_demo_out):
        """The four built-in helpers must be defined (not just called)."""
        body = _read(constraints_demo_out / "constraints.py")
        assert "def count(" in body
        assert "def sum_power(" in body
        assert "def avg_power(" in body
        assert "def max_power(" in body

    def test_constraints_module_uses_threading_lock(self, constraints_demo_out):
        """The design doc requires a thread-safe registry."""
        body = _read(constraints_demo_out / "constraints.py")
        assert "threading.Lock" in body
        assert "_registry_lock" in body
        assert "_registry" in body

    def test_constraints_module_exposes_register_peripheral(self, constraints_demo_out):
        body = _read(constraints_demo_out / "constraints.py")
        assert "def register_peripheral" in body

    def test_constraints_module_exposes_failure_counter(self, constraints_demo_out):
        body = _read(constraints_demo_out / "constraints.py")
        assert "constraint_failures" in body

    def test_constraints_module_uses_logging_for_failures(self, constraints_demo_out):
        body = _read(constraints_demo_out / "constraints.py")
        assert "logging" in body
        # Design doc requires logging.warning for constraint violations
        assert "warning" in body.lower() or "WARNING" in body


class TestConstraintMessagePreserved:
    def test_all_four_messages_present(self, constraints_demo_out):
        """Every CONSTRAINT's MESSAGE string is preserved in the generated code."""
        body = _read(constraints_demo_out / "constraints.py")
        assert "Building code requires at least 2 sensors for redundancy" in body
        assert "Total peripheral power exceeds 500 mW facility limit" in body
        assert "All 5 peripherals must have connections" in body
        assert "At least one actuator required for emergency alerts" in body

    def test_all_four_constraint_names_present(self, constraints_demo_out):
        body = _read(constraints_demo_out / "constraints.py")
        assert "sensor_redundancy" in body
        assert "power_ceiling" in body
        assert "all_connected" in body
        assert "has_actuators" in body

    def test_predicates_call_helper_functions(self, constraints_demo_out):
        """The generated predicates must use the helper functions (count, sum_power)."""
        body = _read(constraints_demo_out / "constraints.py")
        # Predicates are lambdas that call the helpers
        assert "count(" in body
        assert "sum_power(" in body

    def test_predicate_for_power_ceiling_includes_numeric_threshold(self, constraints_demo_out):
        """The power_ceiling predicate must encode the 500 mW threshold."""
        body = _read(constraints_demo_out / "constraints.py")
        # 500 mW → 500.0 after unit normalization
        assert "500" in body


class TestNoConstraintsBackwardCompat:
    def test_constraints_module_not_emitted_without_constraints(self, multi_periph_out):
        """A model with no CONSTRAINTs must NOT produce a constraints.py file."""
        assert not (multi_periph_out / "constraints.py").exists()

    def test_other_files_still_generated(self, multi_periph_out):
        """Backwards-compat: removing constraints must not break other emissions."""
        # alerts.py is emitted for every model by the RPi generator
        assert (multi_periph_out / "alerts.py").is_file()
        assert (multi_periph_out / "common.py").is_file()
        assert (multi_periph_out / "msg.py").is_file()


class TestGenerationDeterminism:
    def test_regen_is_byte_identical(self, device_mm, tmp_path):
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"
        model_path = "examples/rpi/rpi_constraints_demo.dev"
        RPiCodeGenerator(device_mm.model_from_file(model_path), out1).generate()
        RPiCodeGenerator(device_mm.model_from_file(model_path), out2).generate()
        # Compare the constraints.py file across two runs
        c1 = _read(out1 / "constraints.py")
        c2 = _read(out2 / "constraints.py")
        assert c1 == c2
        # Also verify no spurious differences across the whole tree
        out1_files = sorted(p.relative_to(out1) for p in out1.rglob("*") if p.is_file())
        out2_files = sorted(p.relative_to(out2) for p in out2.rglob("*") if p.is_file())
        assert out1_files == out2_files
        for rel in out1_files:
            assert (out1 / rel).read_bytes() == (out2 / rel).read_bytes()


class TestEndToEndCli:
    def test_demol_generate_rpi_produces_constraints_py(self, tmp_path):
        """End-to-end: ``demol generate rpi`` must produce a valid constraints.py."""
        result = subprocess.run(
            [
                "demol",
                "generate",
                "rpi",
                "examples/rpi/rpi_constraints_demo.dev",
                "--output-dir",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"demol generate failed: stdout={result.stdout!r} stderr={result.stderr!r}"
        # Walk the output tree to find the constraints.py (RPi generator does not
        # create subdirectories, so it lives directly under tmp_path)
        candidates = list(tmp_path.rglob("constraints.py"))
        assert candidates, f"no constraints.py produced under {tmp_path}"
        target = candidates[0]
        body = target.read_text(encoding="utf-8")
        # must contain the check function and at least one helper
        assert "def check_constraints" in body
        assert "def count(" in body


class TestGeneratedRuntimeImports:
    """End-to-end: the emitted constraints.py must be importable and behave
    correctly when invoked against a small in-memory registry."""

    def test_emitted_module_imports(self, constraints_demo_out):
        import importlib.util

        path = constraints_demo_out / "constraints.py"
        spec = importlib.util.spec_from_file_location("constraints", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # would raise on NameError

    def test_check_constraints_against_minimal_registry(self, constraints_demo_out):
        import importlib.util

        path = constraints_demo_out / "constraints.py"
        spec = importlib.util.spec_from_file_location("constraints_rt", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Register 2 sensors + 1 actuator; all_connected (>=5) must fail
        module.register_peripheral("S1", "SENSOR", 12.0)
        module.register_peripheral("S2", "SENSOR", 12.0)
        module.register_peripheral("A1", "ACTUATOR", 80.0)
        violations = module.check_constraints()
        # sensor_redundancy: 2 >= 2 OK, power_ceiling: 104 < 500 OK,
        # all_connected: 3 >= 5 FAIL, has_actuators: 1 >= 1 OK
        assert violations == 1
        assert module.constraint_failures == 1
