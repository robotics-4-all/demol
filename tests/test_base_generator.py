"""Tests for the BaseCodeGenerator CONSTRAINT helper methods.

These helpers are consumed by per-backend code generators (RPi, RIOT, Zephyr)
in T11-T13.  This module focuses on the base class API:

  * ``get_constraint_runtime_check(model)``         -> multi-line str
  * ``render_constraint_predicate(constraint, backend)`` -> str
  * ``_render_python_predicate(constraint)``        -> str
  * ``_render_c_predicate(constraint)``             -> str
  * ``_get_constraint_functions()``                 -> Dict[str, str]

The default base implementation targets C-style runtimes (riotos/zephyr); the
RPi generator is expected to override ``_get_constraint_functions`` to return
Python-friendly function names in T11.
"""
import jinja2
import pytest
from pathlib import Path

from demol.transformations.base_generator import BaseCodeGenerator


# ---------------------------------------------------------------------------
# Inline model fixtures
# ---------------------------------------------------------------------------

# Minimal valid base model.  Mirrors the BASE_MODEL pattern used in
# tests/test_user_constraints.py so the test suite stays self-contained.
BASE_MODEL = """
DEVICE TestDevice WITH description="test", author="test", os=raspbian;
NETWORK[WiFi] WITH ssid="test", password="test";
BROKER[MQTT] test WITH host="localhost", port=1883;

USE RaspberryPi_5_8GB;
USE BME680[Sensor1];

CONNECT Sensor1 WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";
"""


# ---------------------------------------------------------------------------
# Test-only concrete subclass of BaseCodeGenerator
# ---------------------------------------------------------------------------


class _StubGen(BaseCodeGenerator):
    """A trivial concrete subclass used to instantiate the abstract base.

    Mirrors what RPiCodeGenerator does (sets ``OS`` to a backend tag and
    implements the two abstract methods), but without bringing Jinja template
    or filesystem side-effects into the test.
    """

    OS = "raspbian"

    def __init__(self, device_model, output_dir):
        super().__init__(device_model, output_dir)

    def generate(self) -> None:
        """No-op: this stub does not write any code."""
        return None

    def setup_template_environment(self) -> jinja2.Environment:
        """Return a minimal Jinja2 environment with the loader disabled."""
        return jinja2.Environment(loader=jinja2.BaseLoader())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_gen(device_mm):
    """A stub generator bound to a model that has no CONSTRAINT blocks."""
    model = device_mm.model_from_str(BASE_MODEL)
    return _StubGen(model, Path("/tmp/demol_test_stub_out"))


@pytest.fixture
def stub_gen_with_constraint(device_mm):
    """A stub generator bound to a model that has a single CONSTRAINT block."""
    model_str = (
        BASE_MODEL
        + """
    CONSTRAINT c1: count(SENSOR) < 10;
    """
    )
    model = device_mm.model_from_str(model_str)
    return _StubGen(model, Path("/tmp/demol_test_stub_out"))


@pytest.fixture
def stub_gen_with_multi_constraint(device_mm):
    """A stub generator bound to a model with multiple CONSTRAINTs."""
    model_str = (
        BASE_MODEL
        + """
    CONSTRAINT max_sensors: count(SENSOR) < 10;
    CONSTRAINT power_budget: sum_power(PERIPHERAL) < 5000.0 mW;
    """
    )
    model = device_mm.model_from_str(model_str)
    return _StubGen(model, Path("/tmp/demol_test_stub_out"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_constraint_runtime_check_empty_when_no_constraints(stub_gen):
    """When the model has no CONSTRAINTs, the helper returns an empty string.

    The generators must be able to call this method unconditionally and
    simply emit zero output for models that opt out of CONSTRAINTs.
    """
    model = stub_gen.device_model
    assert list(getattr(model, "constraints", []) or []) == []
    assert stub_gen.get_constraint_runtime_check(model) == ""


def test_get_constraint_runtime_check_contains_model_name(stub_gen_with_constraint):
    """The emitted runtime check block must mention the device name."""
    model = stub_gen_with_constraint.device_model
    model_name = model.metadata.name

    output = stub_gen_with_constraint.get_constraint_runtime_check(model)

    assert isinstance(output, str)
    assert len(output) > 0
    assert model_name in output


def test_get_constraint_runtime_check_includes_constraint_name(stub_gen_with_constraint):
    """The emitted block must reference each declared constraint by name."""
    model = stub_gen_with_constraint.device_model

    output = stub_gen_with_constraint.get_constraint_runtime_check(model)

    for c in model.constraints:
        assert c.name in output


def test_get_constraint_runtime_check_uses_helper_functions(stub_gen_with_multi_constraint):
    """The emitted block must declare the runtime helper functions it uses.

    The stub generator defaults to the Python (raspbian) backend, so we
    ask for the C backend explicitly to assert the C-style helper names
    show up in the generated block.
    """
    model = stub_gen_with_multi_constraint.device_model
    funcs = stub_gen_with_multi_constraint._get_constraint_functions()

    output = stub_gen_with_multi_constraint.get_constraint_runtime_check(
        model, backend="riotos"
    )

    # The block must mention at least the helpers it actually invokes.
    invoked = {funcs["count"], funcs["sum_power"]}
    for helper in invoked:
        assert helper in output, f"Expected runtime helper {helper!r} in output"


def test_get_constraint_runtime_check_python_uses_raw_names(stub_gen_with_multi_constraint):
    """The Python runtime check must reference DSL builtin names directly."""
    model = stub_gen_with_multi_constraint.device_model

    output = stub_gen_with_multi_constraint.get_constraint_runtime_check(
        model, backend="raspbian"
    )

    # Python predicates use the raw DSL function names (e.g. ``count``,
    # ``sum_power``) so the generated helpers can be plain callables.
    assert "count(" in output
    assert "sum_power(" in output


def test_render_constraint_predicate_python_contains_count(stub_gen_with_constraint):

    """RPi (raspbian) predicates must call a Python helper named ``count``."""
    constraint = stub_gen_with_constraint.device_model.constraints[0]

    pred = stub_gen_with_constraint.render_constraint_predicate(constraint, "raspbian")

    assert isinstance(pred, str)
    assert "count(" in pred
    # And it must mention the argument type.
    assert "SENSOR" in pred


def test_render_constraint_predicate_riot_contains_count_underscore(stub_gen_with_constraint):
    """RIOT (C) predicates must call a C helper whose name starts with ``count_``."""
    constraint = stub_gen_with_constraint.device_model.constraints[0]

    pred = stub_gen_with_constraint.render_constraint_predicate(constraint, "riotos")

    assert isinstance(pred, str)
    assert "count_" in pred


def test_render_constraint_predicate_zephyr_contains_count_underscore(stub_gen_with_constraint):
    """Zephyr (C) predicates must call a C helper whose name starts with ``count_``."""
    constraint = stub_gen_with_constraint.device_model.constraints[0]

    pred = stub_gen_with_constraint.render_constraint_predicate(constraint, "zephyr")

    assert isinstance(pred, str)
    assert "count_" in pred


def test_render_constraint_predicate_unknown_backend_raises(stub_gen_with_constraint):
    """Unsupported backends must surface a clear error rather than silently failing."""
    constraint = stub_gen_with_constraint.device_model.constraints[0]
    with pytest.raises(ValueError):
        stub_gen_with_constraint.render_constraint_predicate(constraint, "arduino")


def test_render_constraint_predicate_dispatch_is_overridable(stub_gen_with_constraint):
    """Subclasses must be able to override either renderer independently."""
    constraint = stub_gen_with_constraint.device_model.constraints[0]

    class _CustomGen(_StubGen):
        def _render_c_predicate(self, constraint):  # noqa: D401 - test stub
            return "CUSTOM_C"

    custom = _CustomGen(
        stub_gen_with_constraint.device_model,
        Path("/tmp/demol_test_stub_out"),
    )
    assert custom.render_constraint_predicate(constraint, "riotos") == "CUSTOM_C"
    # The Python path must NOT be affected by overriding the C renderer.
    assert "count(" in custom.render_constraint_predicate(constraint, "raspbian")


def test_get_constraint_functions_has_required_keys(stub_gen):
    """The runtime function table must declare the four built-ins."""
    funcs = stub_gen._get_constraint_functions()
    assert isinstance(funcs, dict)
    for required in ("count", "sum_power", "avg_power", "max_power"):
        assert required in funcs
        assert isinstance(funcs[required], str)
        assert funcs[required]  # non-empty


def test_get_constraint_functions_is_overridable(stub_gen):
    """Subclasses must be able to override the helper-naming table."""
    class _CustomGen(_StubGen):
        def _get_constraint_functions(self):
            return {"count": "py_count", "sum_power": "py_sum", "avg_power": "py_avg", "max_power": "py_max"}

    custom = _CustomGen(
        stub_gen.device_model,
        Path("/tmp/demol_test_stub_out"),
    )
    assert custom._get_constraint_functions()["count"] == "py_count"


def test_get_constraint_runtime_check_explicit_backend(stub_gen_with_constraint):
    """Passing ``backend`` explicitly must override the generator's default OS."""
    model = stub_gen_with_constraint.device_model

    py_output = stub_gen_with_constraint.get_constraint_runtime_check(model, backend="raspbian")
    c_output = stub_gen_with_constraint.get_constraint_runtime_check(model, backend="riotos")

    # Python output should reference the model + a Python-style predicate.
    assert model.metadata.name in py_output
    assert "count(" in py_output

    # C output should reference the model + a C-style predicate.
    assert model.metadata.name in c_output
    assert "count_" in c_output
