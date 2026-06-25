"""String-level emission tests for ALERT trigger codegen on the Zephyr target.

Covers the contract documented in ``docs/alert-runtime-design.md`` Section 5:
- ``check_alerts()`` is emitted in ``main.c`` when the model declares at least one
  ALERT block
- A model with no ALERTs produces NO ``check_alerts()`` and NO cooldown statics
  (backward compat — non-ALERT examples remain byte-identical)
- A ``static int64_t last_trigger_<name>_ms`` cooldown gate is emitted per ALERT
  and compared against ``k_uptime_get()``
- The condition predicate renders as a C boolean expression using
  ``<peripheral>_data.<property>`` field references declared in the
  ``FOR zephyr`` PROPERTIES of the source ``.hwd``
- For ``PUBLISH`` actions, a ``LOG_INF`` placeholder is emitted (full MQTT
  publish wiring is owned by T16)
- For ``ACTIVATE`` actions, a ``gpio_pin_set`` placeholder is emitted
- Generation is deterministic: two runs produce byte-identical output
"""

from pathlib import Path
from textwrap import dedent

import pytest

from demol.transformations.m2t_zephyr import m2t_zephyr


PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Real-world ALERT example from examples/esp/ — two PUBLISH alerts on a BME680
# with 60 hz / 30 hz cooldowns (treated as 60/30 sec by cooldown_to_seconds
# with a logged warning).
WEMOS_BME680_ALERT_DEV = PROJECT_ROOT / "examples" / "esp" / "wemos_bme680_alert.dev"


# Inline model with two ALERTs — mirrors the real example's shape so the
# test can pin behavior without depending on disk content.
ZEPHYR_ALERT_MODEL = dedent("""\
    DEVICE ZephyrAlertTest WITH description="zephyr alert codegen test",
                                author="demol-tests";

    NETWORK[WiFi] WITH ssid="test", password="test";
    BROKER[MQTT] TestBroker WITH host="localhost", port=1883;

    USE WemosD1Mini;
    USE BME680[Env];

    CONNECT Env WITH
        POWER gnd -- gnd, vcc -- power_5v
        DATA i2c[slave_address=0x76] sda sda -- d2, scl scl -- d1
        @ "test.bme680";

    ALERT fever_alert ON Env WHEN temperature > 38.5
        THEN
            PUBLISH "test.alerts.fever"
        COOLDOWN 60 hz;

    ALERT humid_alert ON Env WHEN humidity > 75.0
        THEN
            PUBLISH "test.alerts.humidity"
        COOLDOWN 30 hz;
    """)


# No-alert variant — same peripherals/connections, just no ALERT block.
# Mirrors ZEPHYR_NO_CONSTRAINT_MODEL in test_zephyr_constraint_codegen.py so
# the backward-compat assertions are easy to compare.
ZEPHYR_NO_ALERT_MODEL = dedent("""\
    DEVICE ZephyrNoAlert WITH description="zephyr no-alert test",
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
def alert_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_alert")
    model = device_mm.model_from_str(ZEPHYR_ALERT_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def no_alert_out(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("zephyr_no_alert")
    model = device_mm.model_from_str(ZEPHYR_NO_ALERT_MODEL)
    m2t_zephyr(model, output_dir=str(out))
    return out


@pytest.fixture(scope="module")
def real_alert_out(device_mm, tmp_path_factory):
    """Real wemos_bme680_alert.dev end-to-end coverage."""
    out = tmp_path_factory.mktemp("zephyr_real_alert")
    model = device_mm.model_from_file(str(WEMOS_BME680_ALERT_DEV))
    m2t_zephyr(model, output_dir=str(out))
    return out


class TestCheckAlertsFunctionEmitted:
    """When the model declares at least one ALERT, check_alerts() must be
    emitted in main.c and invoked from the main loop.
    """

    def test_check_alerts_function_definition(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "void check_alerts" in body, "check_alerts() definition missing from main.c"

    def test_check_alerts_called_from_main(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "check_alerts()" in body, "main() must invoke check_alerts()"

    def test_includes_logging_header(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "<zephyr/logging/log.h>" in body, "main.c must include <zephyr/logging/log.h>"

    def test_log_module_register_present(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "LOG_MODULE_REGISTER" in body, "main.c must call LOG_MODULE_REGISTER"


class TestCooldownGatesEmitted:
    """Per-alert static int64_t last_trigger_<name>_ms gate must be present."""

    def test_first_alert_has_static_var(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "static int64_t last_trigger_fever_alert_ms" in body, \
            "missing static last_trigger_fever_alert_ms"

    def test_second_alert_has_static_var(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "static int64_t last_trigger_humid_alert_ms" in body, \
            "missing static last_trigger_humid_alert_ms"

    def test_cooldown_uses_k_uptime_get(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "k_uptime_get" in body, "cooldown gate must use k_uptime_get()"

    def test_cooldown_value_in_ms(self, alert_out):
        """60 sec → 60000 ms and 30 sec → 30000 ms must be in the gate logic."""
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "60000" in body, "missing 60000 ms (60 sec) cooldown gate"
        assert "30000" in body, "missing 30000 ms (30 sec) cooldown gate"


class TestConditionRendersAsCBool:
    """The condition predicate must render as a C boolean expression using
    the FOR-zephyr PROPERTIES field references.
    """

    def test_temperature_property_referenced(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "bme680_data.temperature" in body, \
            "condition must reference bme680_data.temperature (FOR zephyr property)"

    def test_humidity_property_referenced(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "bme680_data.humidity" in body, \
            "condition must reference bme680_data.humidity (FOR zephyr property)"

    def test_uses_inequality_operator(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert ">" in body, "condition must use the > comparison operator"

    def test_condition_is_boolean_expression(self, alert_out):
        """The condition must be wrapped in a C boolean context (e.g., an if)."""
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "if ((" in body or "if (bme680_data" in body, \
            "condition must be wrapped in an if (...) C boolean expression"


class TestPublishActionPlaceholder:
    """PUBLISH actions must emit a LOG_INF placeholder (T16 owns real MQTT)."""

    def test_log_inf_publish_placeholder(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "LOG_INF" in body, "PUBLISH action must emit a LOG_INF placeholder"

    def test_topic_string_present(self, alert_out):
        body = _read(alert_out / "app" / "src" / "main.c")
        assert "test.alerts.fever" in body, "PUBLISH topic for fever_alert missing"
        assert "test.alerts.humidity" in body, "PUBLISH topic for humid_alert missing"


class TestNoAlertBackwardCompat:
    """When the model has no ALERTs, main.c must NOT contain check_alerts or
    cooldown statics (goldens stay byte-identical for non-ALERT examples).
    """

    def test_no_check_alerts_when_no_alerts(self, no_alert_out):
        body = _read(no_alert_out / "app" / "src" / "main.c")
        assert "check_alerts" not in body, \
            "no-alert model must NOT emit check_alerts"

    def test_no_cooldown_statics_when_no_alerts(self, no_alert_out):
        body = _read(no_alert_out / "app" / "src" / "main.c")
        assert "last_trigger_" not in body, \
            "no-alert model must NOT emit last_trigger_* statics"

    def test_no_log_module_register_when_no_alerts(self, no_alert_out):
        body = _read(no_alert_out / "app" / "src" / "main.c")
        assert "LOG_MODULE_REGISTER" not in body, \
            "no-alert model must NOT emit LOG_MODULE_REGISTER (backward compat)"


class TestRealAlertExample:
    """End-to-end coverage using examples/esp/wemos_bme680_alert.dev."""

    def test_real_example_generates_main_c(self, real_alert_out):
        assert (real_alert_out / "app" / "src" / "main.c").is_file()

    def test_real_example_has_check_alerts(self, real_alert_out):
        body = _read(real_alert_out / "app" / "src" / "main.c")
        assert "check_alerts" in body

    def test_real_example_has_both_cooldown_gates(self, real_alert_out):
        body = _read(real_alert_out / "app" / "src" / "main.c")
        assert "last_trigger_fever_alert_ms" in body
        assert "last_trigger_humid_alert_ms" in body

    def test_real_example_uses_bme680_data(self, real_alert_out):
        body = _read(real_alert_out / "app" / "src" / "main.c")
        assert "bme680_data.temperature" in body
        assert "bme680_data.humidity" in body


class TestGenerationDeterminism:
    """Re-generation must be byte-identical (template uses no time/random)."""

    def test_regen_is_byte_identical(self, device_mm, tmp_path):
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"
        model = device_mm.model_from_str(ZEPHYR_ALERT_MODEL)
        m2t_zephyr(model, output_dir=str(out1))
        m2t_zephyr(model, output_dir=str(out2))

        c1 = _read(out1 / "app" / "src" / "main.c")
        c2 = _read(out2 / "app" / "src" / "main.c")
        assert c1 == c2, "main.c with ALERTs is not deterministic across runs"
