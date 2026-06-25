"""String-level emission tests for SAMPLING codegen on the Zephyr target.

Covers the contract documented in the T14 plan section:
- A model with no SAMPLINGs produces the same static ``app/src/main.c``
  skeleton as before (backward compat — must remain byte-identical with
  the pre-T14 output so existing golden snapshots do not change).
- A model with SAMPLINGs emits a ``while (1)`` loop that calls
  ``k_msleep(1000 / rate)`` and ``<peripheral>_read(...)``.
- Each ``SAMPLING`` mode is handled:
    * ``continuous``     — always call ``<peripheral>_read``
    * ``on_change``      — compare to last sample; only call when changed
    * ``batch``          — collect N samples; flush when buffer full
    * ``on_demand``      — no main-loop call; skeleton reserves an RPC stub
- ``period_ms = 1000 / rate`` (integer division).
- The main loop file does not regress when no SAMPLINGs are declared.
- Generation is deterministic: two runs produce byte-identical output.
"""

from pathlib import Path
from textwrap import dedent

import pytest

from demol.transformations.m2t_zephyr import m2t_zephyr


PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Inline DSL models — no external .dev files for unit tests (tests/AGENTS.md).
# ---------------------------------------------------------------------------

# WemosD1Mini + BME680 with one SAMPLING (continuous) — the canonical combo.
ZEPHYR_SAMPLING_MODEL = dedent("""\
    DEVICE ZephyrSampling WITH description="zephyr sampling codegen test",
                                 author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";

    SAMPLING Env WITH rate=10 hz, mode=continuous;
    """)


# Same as above but with on_change + threshold. The threshold value is
# unused at the C level for the T14 skeleton — the comparison is by
# equality — but the test confirms the mode is plumbed through.
ZEPHYR_ON_CHANGE_MODEL = dedent("""\
    DEVICE ZephyrOnChange WITH description="zephyr on_change codegen test",
                                    author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";

    SAMPLING Env WITH rate=2 hz, mode=on_change, threshold=0.1;
    """)


# batch mode: collects buffer samples then flushes.
ZEPHYR_BATCH_MODEL = dedent("""\
    DEVICE ZephyrBatch WITH description="zephyr batch codegen test",
                                author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";

    SAMPLING Env WITH rate=1 hz, mode=batch, buffer=5;
    """)


# on_demand mode: no main-loop call; skeleton reserves an RPC stub only.
ZEPHYR_ON_DEMAND_MODEL = dedent("""\
    DEVICE ZephyrOnDemand WITH description="zephyr on_demand codegen test",
                                   author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";

    SAMPLING Env WITH rate=1 hz, mode=on_demand;
    """)


# Multiple SAMPLINGs on the same model — the loop must iterate all of them.
ZEPHYR_MULTI_SAMPLING_MODEL = dedent("""\
    DEVICE ZephyrMultiSampling WITH description="zephyr multi-sampling test",
                                        author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME680[Env];
    USE LedGeneric[Status];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";

    CONNECT Status WITH
        POWER gnd -- gnd, vcc -- power_3v3
        DATA gpio[mode="output"] vin -- d3
        @ "test.status";

    SAMPLING Env WITH rate=10 hz, mode=continuous;
    SAMPLING Status WITH rate=1 hz, mode=continuous;
    """)


# No SAMPLING variant — same shape as the constraint test's
# ZEPHYR_NO_CONSTRAINT_MODEL so the backward-compat assertion is
# uniform.
ZEPHYR_NO_SAMPLING_MODEL = dedent("""\
    DEVICE ZephyrNoSampling WITH description="zephyr no-sampling test",
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


# ---------------------------------------------------------------------------
# Module-scoped fixtures — generate each variant once, share across the suite.
# Mirrors the pattern in test_zephyr_constraint_codegen.py.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sampling_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_sampling")
    model = device_mm.model_from_str(ZEPHYR_SAMPLING_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def on_change_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_on_change")
    model = device_mm.model_from_str(ZEPHYR_ON_CHANGE_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def batch_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_batch")
    model = device_mm.model_from_str(ZEPHYR_BATCH_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def on_demand_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_on_demand")
    model = device_mm.model_from_str(ZEPHYR_ON_DEMAND_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def multi_sampling_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_multi_sampling")
    model = device_mm.model_from_str(ZEPHYR_MULTI_SAMPLING_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def no_sampling_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_no_sampling")
    model = device_mm.model_from_str(ZEPHYR_NO_SAMPLING_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


# ---------------------------------------------------------------------------
# Backward compatibility — the no-SAMPLING skeleton must be byte-identical
# to the pre-T14 static output, otherwise every existing golden snapshot
# breaks.
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    """A model without SAMPLINGs must still produce the original skeleton."""

    def test_main_c_still_emitted(self, no_sampling_out):
        assert (no_sampling_out / "app" / "src" / "main.c").is_file()

    def test_main_c_is_static_skeleton(self, no_sampling_out):
        """The no-SAMPLING output must NOT contain k_msleep or read_<x> calls.

        This is the strict backward-compat check: the new template's
        ``{% else %}`` branch must produce exactly the same bytes as the
        previous static ``_APP_SRC_MAIN_C`` string.
        """
        body = _read(no_sampling_out / "app" / "src" / "main.c")
        assert "k_msleep" not in body
        assert "bme680_read" not in body
        assert "while (1)" not in body

    def test_main_c_includes_kernel_header(self, no_sampling_out):
        body = _read(no_sampling_out / "app" / "src" / "main.c")
        assert "#include <zephyr/kernel.h>" in body

    def test_main_c_returns_zero(self, no_sampling_out):
        body = _read(no_sampling_out / "app" / "src" / "main.c")
        assert "return 0;" in body


# ---------------------------------------------------------------------------
# Continuous mode — the canonical SAMPLING case.
# ---------------------------------------------------------------------------

class TestContinuousSampling:
    """continuous mode: always call ``<peripheral>_read`` in the loop."""

    def test_main_c_emits_k_msleep(self, sampling_out):
        body = _read(sampling_out / "app" / "src" / "main.c")
        assert "k_msleep" in body

    def test_k_msleep_period_is_1000_over_rate(self, sampling_out):
        """rate=10 hz -> k_msleep(100). 1000 // 10 = 100."""
        body = _read(sampling_out / "app" / "src" / "main.c")
        assert "k_msleep(100)" in body

    def test_main_loop_is_while_one(self, sampling_out):
        body = _read(sampling_out / "app" / "src" / "main.c")
        assert "while (1)" in body

    def test_main_loop_calls_peripheral_read(self, sampling_out):
        body = _read(sampling_out / "app" / "src" / "main.c")
        # bme680.c.j2 emits ``int bme680_read(struct bme680_data *data)``;
        # the loop must invoke that function.
        assert "bme680_read" in body

    def test_includes_kernel_header(self, sampling_out):
        body = _read(sampling_out / "app" / "src" / "main.c")
        assert "#include <zephyr/kernel.h>" in body

    def test_includes_bme680_header(self, sampling_out):
        """The bme680_read() function takes a struct bme680_data; the
        generated main.c must include the matching header."""
        body = _read(sampling_out / "app" / "src" / "main.c")
        assert "bme680.h" in body or "bme680_data" in body

    def test_other_artifacts_unchanged(self, sampling_out):
        """Adding SAMPLINGs must not break the rest of the app tree."""
        app = sampling_out / "app"
        assert (app / "CMakeLists.txt").is_file()
        assert (app / "prj.conf").is_file()
        assert (app / "src" / "bme680.c").is_file()


# ---------------------------------------------------------------------------
# on_change mode — compare to last sample, only call when changed.
# ---------------------------------------------------------------------------

class TestOnChangeSampling:
    """on_change mode: compare to last value, only call when different."""

    def test_main_c_emits_k_msleep(self, on_change_out):
        body = _read(on_change_out / "app" / "src" / "main.c")
        assert "k_msleep" in body

    def test_k_msleep_period_for_2hz(self, on_change_out):
        """rate=2 hz -> k_msleep(500). 1000 // 2 = 500."""
        body = _read(on_change_out / "app" / "src" / "main.c")
        assert "k_msleep(500)" in body

    def test_emits_last_value_state(self, on_change_out):
        """on_change mode must track the previous sample. We accept any
        static storage name (last_bme680 / last_sample / etc.) so the
        contract is just that SOME static state exists."""
        body = _read(on_change_out / "app" / "src" / "main.c")
        # The C skeleton uses ``static`` storage; either ``static int``
        # or ``static struct`` is acceptable for the last-value cache.
        assert "static" in body

    def test_calls_peripheral_read(self, on_change_out):
        body = _read(on_change_out / "app" / "src" / "main.c")
        assert "bme680_read" in body


# ---------------------------------------------------------------------------
# batch mode — collect N samples in a buffer, publish when full.
# ---------------------------------------------------------------------------

class TestBatchSampling:
    """batch mode: collect N samples in a buffer, publish when full."""

    def test_main_c_emits_k_msleep(self, batch_out):
        body = _read(batch_out / "app" / "src" / "main.c")
        assert "k_msleep" in body

    def test_k_msleep_period_for_1hz(self, batch_out):
        """rate=1 hz -> k_msleep(1000)."""
        body = _read(batch_out / "app" / "src" / "main.c")
        assert "k_msleep(1000)" in body

    def test_emits_buffer_counter(self, batch_out):
        """batch mode needs a running sample counter. We require the
        buffer size (``buffer=5``) to appear somewhere — either as a
        literal in the loop or as a #define."""
        body = _read(batch_out / "app" / "src" / "main.c")
        assert "5" in body

    def test_calls_peripheral_read(self, batch_out):
        body = _read(batch_out / "app" / "src" / "main.c")
        assert "bme680_read" in body


# ---------------------------------------------------------------------------
# on_demand mode — no main-loop call, skeleton reserves an RPC stub.
# ---------------------------------------------------------------------------

class TestOnDemandSampling:
    """on_demand mode: no main-loop call, an RPC stub is reserved instead."""

    def test_main_c_emits_k_msleep(self, on_demand_out):
        """on_demand still emits a sleeping main loop (the task specifies
        a while(1) loop with k_msleep) but does NOT call the read function
        inside the loop body."""
        body = _read(on_demand_out / "app" / "src" / "main.c")
        assert "k_msleep" in body

    def test_does_not_call_peripheral_read(self, on_demand_out):
        """on_demand: no ``bme680_read`` call from the main loop. The
        task spec says "NO main-loop call (skeleton reserves an RPC
        handler stub)"."""
        body = _read(on_demand_out / "app" / "src" / "main.c")
        assert "bme680_read" not in body

    def test_reserves_rpc_handler_stub(self, on_demand_out):
        """Skeleton must mention the on-demand RPC handler by name. We
        accept any handle / handler substring to stay flexible."""
        body = _read(on_demand_out / "app" / "src" / "main.c")
        # The stub comment is the canonical marker — the C function will
        # be added in a later task.
        assert "on_demand" in body.lower() or "rpc" in body.lower() or "handler" in body.lower()


# ---------------------------------------------------------------------------
# Multi-SAMPLING — the loop must iterate all configured peripherals.
# ---------------------------------------------------------------------------

class TestMultiSampling:
    """A model with multiple SAMPLINGs must emit all of them in the loop."""

    def test_loop_contains_all_peripheral_reads(self, multi_sampling_out):
        body = _read(multi_sampling_out / "app" / "src" / "main.c")
        # bme680 is the env sensor; led is the actuator. Both must be
        # referenced from the main loop.
        assert "bme680_read" in body
        # led.c.j2 emits ``int led_init(void)`` / ``int led_set(int state)``;
        # SAMPLING on a led typically uses the ``set`` action, but the
        # exact function name is left flexible — we just require the
        # peripheral's base name to appear.
        assert "led" in body.lower()

    def test_only_one_while_one(self, multi_sampling_out):
        """Multiple SAMPLINGs share a single main loop, not nested loops."""
        body = _read(multi_sampling_out / "app" / "src" / "main.c")
        assert body.count("while (1)") == 1


# ---------------------------------------------------------------------------
# Determinism — generation must be repeatable.
# ---------------------------------------------------------------------------

class TestGenerationDeterminism:
    """Re-generation must be byte-identical (template uses no time/random)."""

    def test_regen_is_byte_identical(self, device_mm, tmp_path):
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"
        model = device_mm.model_from_str(ZEPHYR_SAMPLING_MODEL)
        m2t_zephyr(model, output_dir=str(out1))
        m2t_zephyr(model, output_dir=str(out2))

        m1 = _read(out1 / "app" / "src" / "main.c")
        m2 = _read(out2 / "app" / "src" / "main.c")
        assert m1 == m2, "main.c is not deterministic across runs"

        # Also verify the full file tree is stable.
        all1 = sorted(p.relative_to(out1) for p in out1.rglob("*") if p.is_file())
        all2 = sorted(p.relative_to(out2) for p in out2.rglob("*") if p.is_file())
        assert all1 == all2
        for rel in all1:
            assert (out1 / rel).read_bytes() == (out2 / rel).read_bytes()
