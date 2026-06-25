"""String-level emission tests for CONSTRAINT runtime codegen on the Zephyr target.

Covers the contract documented in ``docs/constraint-runtime-design.md`` Section 4:
- ``constraint.c`` and ``constraint.h`` are emitted when the model declares constraints
- A model with no constraints produces NO ``constraint.c`` / ``constraint.h`` (backward compat)
- ``constraint.c`` defines ``void check_constraints(void)`` and exposes thread-safe
  helpers via ``k_mutex`` (``k_mutex_lock`` / ``k_mutex_unlock``)
- A ``k_work_delayable`` periodically invokes the check (Zephyr workqueue)
- ``constraint.h`` declares the ``struct periph_state`` layout and the public API
- ``app/CMakeLists.txt`` includes ``src/constraint.c`` in ``target_sources()`` when
  constraints are declared
- Generation is deterministic: two runs produce byte-identical output
"""

from pathlib import Path
from textwrap import dedent

import pytest

from demol.transformations.m2t_zephyr import m2t_zephyr


PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Inline model with one CONSTRAINT — task requires inline model, no new
# examples/esp/ file. WemosD1Mini + BME680 is the canonical combo in
# test_zephyr_codegen.SYNTHETIC_BME680_MODEL, so we mirror that here and
# just add a single CONSTRAINT block to exercise codegen.
ZEPHYR_CONSTRAINT_MODEL = dedent("""\
    DEVICE ZephyrConstraints WITH description="zephyr constraint codegen test",
                                  author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";

    CONSTRAINT power_ceiling: sum_power(PERIPHERAL) < 500 mW
        MESSAGE "Total peripheral power exceeds 500 mW facility limit";
    """)


# Multi-constraint variant — covers the {% for c in model.constraints %}
# loop body. All three predicates are intentionally simple so the
# generated C is easy to assert against.
ZEPHYR_MULTI_CONSTRAINT_MODEL = dedent("""\
    DEVICE ZephyrMulti WITH description="zephyr multi constraint test",
                            author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";

    CONSTRAINT sensor_redundancy: count(SENSOR) >= 1
        MESSAGE "Need at least 1 sensor";
    CONSTRAINT power_ceiling: sum_power(PERIPHERAL) < 500 mW
        MESSAGE "Total peripheral power exceeds 500 mW";
    CONSTRAINT all_connected: count(CONNECTION) >= 1
        MESSAGE "Need at least 1 connection";
    """)


# No-constraint variant — same shape, just no CONSTRAINT block. Mirrors
# SYNTHETIC_BME680_MODEL from test_zephyr_codegen to keep the test
# surface uniform.
ZEPHYR_NO_CONSTRAINT_MODEL = dedent("""\
    DEVICE ZephyrNoConstraint WITH description="zephyr no-constraint test",
                                  author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";
    """)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def constraint_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_constraint")
    model = device_mm.model_from_str(ZEPHYR_CONSTRAINT_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def multi_constraint_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_multi_constraint")
    model = device_mm.model_from_str(ZEPHYR_MULTI_CONSTRAINT_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def no_constraint_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_no_constraint")
    model = device_mm.model_from_str(ZEPHYR_NO_CONSTRAINT_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


class TestConstraintFilesEmitted:
    """When the model declares at least one CONSTRAINT, the generator
    must emit constraint.c and constraint.h under app/src/.
    """

    def test_constraint_c_is_emitted(self, constraint_out):
        assert (constraint_out / "app" / "src" / "constraint.c").is_file()

    def test_constraint_h_is_emitted(self, constraint_out):
        assert (constraint_out / "app" / "src" / "constraint.h").is_file()

    def test_no_constraint_skips_files(self, no_constraint_out):
        """Backward compat: a model without CONSTRAINTs must NOT emit the files."""
        assert not (no_constraint_out / "app" / "src" / "constraint.c").exists()
        assert not (no_constraint_out / "app" / "src" / "constraint.h").exists()

    def test_other_app_artifacts_still_emitted(self, constraint_out):
        """Adding constraints must not break the rest of the app tree."""
        app = constraint_out / "app"
        assert (app / "CMakeLists.txt").is_file()
        assert (app / "prj.conf").is_file()
        assert (app / "src" / "main.c").is_file()
        assert (app / "src" / "bme680.c").is_file()


class TestConstraintCStructure:
    """Substring contracts for the generated constraint.c."""

    def test_has_check_constraints_function(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.c")
        assert "void check_constraints" in body

    def test_uses_k_mutex_for_thread_safety(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.c")
        assert "k_mutex" in body
        assert "k_mutex_lock" in body

    def test_uses_k_work_delayable_for_periodic_check(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.c")
        # Either k_work_delayable (delayable work item) or k_work is the
        # Zephyr workqueue primitive that schedules the periodic check.
        assert "k_work" in body

    def test_uses_log_wrn_for_failure_logging(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.c")
        assert "LOG_WRN" in body

    def test_uses_atomic_counter(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.c")
        # Design doc §4.3 requires atomic_t counter for failure tracking
        assert "atomic" in body.lower()

    def test_includes_zephyr_kernel(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.c")
        assert "<zephyr/kernel.h>" in body

    def test_includes_zephyr_logging(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.c")
        assert "<zephyr/logging/log.h>" in body

    def test_register_peripheral_helper(self, constraint_out):
        """Drivers need a registration entry point (design doc §4.1)."""
        body = _read(constraint_out / "app" / "src" / "constraint.c")
        assert "register_peripheral" in body

    def test_uses_constraint_mutex_in_check(self, constraint_out):
        """check_constraints() must hold the mutex while inspecting state."""
        body = _read(constraint_out / "app" / "src" / "constraint.c")
        assert "constraint_mutex" in body

    def test_multi_constraint_iterates_predicates(self, multi_constraint_out):
        """The {% for %} loop must emit one predicate per CONSTRAINT."""
        body = _read(multi_constraint_out / "app" / "src" / "constraint.c")
        # All three constraint names from the inline model must appear
        assert "sensor_redundancy" in body
        assert "power_ceiling" in body
        assert "all_connected" in body


class TestConstraintHStructure:
    """Substring contracts for the generated constraint.h."""

    def test_declares_periph_state_struct(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.h")
        assert "struct periph_state" in body

    def test_declares_extern_k_mutex(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.h")
        # Design doc §4.4: header declares the public API surface.
        # k_mutex is typically opaque in the header.
        assert "k_mutex" in body

    def test_declares_check_constraints_prototype(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.h")
        assert "check_constraints" in body

    def test_declares_register_peripheral_prototype(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.h")
        assert "register_peripheral" in body

    def test_header_guards_present(self, constraint_out):
        body = _read(constraint_out / "app" / "src" / "constraint.h")
        assert "#ifndef" in body
        assert "#define" in body
        assert "#endif" in body

    def test_no_header_when_no_constraints(self, no_constraint_out):
        assert not (no_constraint_out / "app" / "src" / "constraint.h").exists()


class TestCMakeListsIntegration:
    """The CMakeLists.txt must include constraint.c when constraints exist."""

    def test_cmakelists_references_constraint_c(self, constraint_out):
        body = _read(constraint_out / "app" / "CMakeLists.txt")
        assert "constraint.c" in body

    def test_cmakelists_no_constraint_when_empty(self, no_constraint_out):
        body = _read(no_constraint_out / "app" / "CMakeLists.txt")
        assert "constraint.c" not in body


class TestGenerationDeterminism:
    """Re-generation must be byte-identical (template uses no time/random)."""

    def test_regen_is_byte_identical(self, device_mm, tmp_path):
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"
        model = device_mm.model_from_str(ZEPHYR_CONSTRAINT_MODEL)
        m2t_zephyr(model, output_dir=str(out1))
        m2t_zephyr(model, output_dir=str(out2))

        c1 = _read(out1 / "app" / "src" / "constraint.c")
        c2 = _read(out2 / "app" / "src" / "constraint.c")
        assert c1 == c2, "constraint.c is not deterministic across runs"

        h1 = _read(out1 / "app" / "src" / "constraint.h")
        h2 = _read(out2 / "app" / "src" / "constraint.h")
        assert h1 == h2, "constraint.h is not deterministic across runs"

        # Also verify the full file tree is stable (CMakeLists may change
        # the target_sources list, so it has to match too).
        all1 = sorted(p.relative_to(out1) for p in out1.rglob("*") if p.is_file())
        all2 = sorted(p.relative_to(out2) for p in out2.rglob("*") if p.is_file())
        assert all1 == all2
        for rel in all1:
            assert (out1 / rel).read_bytes() == (out2 / rel).read_bytes()


class TestPrjConfNoConstraintArtifacts:
    """The Zephyr Kconfig file is independent of constraints — it should
    not gain or lose entries based on whether constraints are present.
    """

    def test_prj_conf_unchanged_by_constraints(self, constraint_out, no_constraint_out):
        with_constraints = _read(constraint_out / "app" / "prj.conf")
        without_constraints = _read(no_constraint_out / "app" / "prj.conf")
        # Same BME680 model in both fixtures → same Kconfig symbols.
        assert with_constraints == without_constraints
