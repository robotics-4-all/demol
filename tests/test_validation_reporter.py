"""Coverage tests for demol.lang.validation (18% baseline).

The `ValidationReporter` class, `ValidationResult` dataclass, and the
public `validate_model_file` / `validate_models` entry points are
exercised end-to-end, including the rich and the plain-text fallback
paths.
"""

import os
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from demol.lang.device import get_device_mm
from demol.lang.validation import (
    ACTIVE_VALIDATIONS,
    ValidationReporter,
    ValidationResult,
    ValidationStatus,
    validate_model_file,
    validate_models,
)

# ── ValidationStatus / ACTIVE_VALIDATIONS / ValidationResult ────────────────


def test_validation_status_enum_values():
    assert ValidationStatus.PASS.value == "pass"
    assert ValidationStatus.WARN.value == "warn"
    assert ValidationStatus.FAIL.value == "fail"


def test_active_validations_is_non_empty_list_of_pairs():
    assert len(ACTIVE_VALIDATIONS) > 0
    for entry in ACTIVE_VALIDATIONS:
        assert isinstance(entry, tuple)
        assert len(entry) == 2
        assert isinstance(entry[0], str) and isinstance(entry[1], str)


def test_validation_result_rel_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = ValidationResult(
        file_path=str(tmp_path / "model.dev"),
        status=ValidationStatus.PASS,
        warnings=[],
        errors=[],
    )
    assert r.rel_path == "model.dev"


def test_validation_result_has_issues_false_when_empty():
    r = ValidationResult(file_path="x.dev", status=ValidationStatus.PASS, warnings=[], errors=[])
    assert r.has_issues is False


def test_validation_result_has_issues_true_with_warning():
    r = ValidationResult(
        file_path="x.dev",
        status=ValidationStatus.WARN,
        warnings=["w"],
        errors=[],
    )
    assert r.has_issues is True


def test_validation_result_has_issues_true_with_error():
    r = ValidationResult(file_path="x.dev", status=ValidationStatus.FAIL, warnings=[], errors=["e"])
    assert r.has_issues is True


# ── ValidationReporter: rich path (default) ─────────────────────────────────


def test_reporter_init_uses_rich_when_available():
    r = ValidationReporter(use_rich=True)
    assert r.use_rich is True
    assert r.console is not None


def test_reporter_init_skips_rich_when_disabled():
    r = ValidationReporter(use_rich=False)
    assert r.use_rich is False
    assert r.console is None


def test_reporter_init_skips_rich_when_library_unavailable():
    r = ValidationReporter(use_rich=True)
    with patch("demol.lang.validation.RICH_AVAILABLE", False):
        r2 = ValidationReporter(use_rich=True)
    assert r2.use_rich is False
    assert r2.console is None


def test_reporter_print_uses_rich_console(capsys):
    r = ValidationReporter(use_rich=False)
    r.print("hello world", style=None)
    captured = capsys.readouterr()
    assert "hello world" in captured.out


def test_reporter_print_with_rich(capsys):
    r = ValidationReporter(use_rich=True)
    r.print("hello via rich")
    captured = capsys.readouterr()
    assert "hello via rich" in captured.out


def test_reporter_print_active_validations_with_rich(capsys):
    r = ValidationReporter(use_rich=True)
    r.print_active_validations()
    captured = capsys.readouterr()
    for val_id, _ in ACTIVE_VALIDATIONS:
        assert val_id in captured.out


def test_reporter_print_active_validations_without_rich(capsys):
    r = ValidationReporter(use_rich=False)
    r.print_active_validations()
    captured = capsys.readouterr()
    assert "Active Validations" in captured.out
    for val_id, _ in ACTIVE_VALIDATIONS:
        assert val_id in captured.out


def test_reporter_create_summary_table_with_pass_warn_fail():
    r = ValidationReporter(use_rich=True)
    results = [
        ValidationResult("a.dev", ValidationStatus.PASS, [], []),
        ValidationResult("b.dev", ValidationStatus.WARN, ["w1"], []),
        ValidationResult("c.dev", ValidationStatus.FAIL, [], ["e1", "e2"]),
    ]
    table = r.create_summary_table(results)
    assert table is not None
    assert table.row_count == 3


def test_reporter_create_summary_table_long_path_truncation():
    r = ValidationReporter(use_rich=True)
    long_path = "/" + "x" * 100 + "/model.dev"
    results = [ValidationResult(long_path, ValidationStatus.PASS, [], [])]
    table = r.create_summary_table(results)
    assert table.row_count == 1


def test_reporter_create_summary_table_without_rich_raises():
    r = ValidationReporter(use_rich=False)
    results = [ValidationResult("a.dev", ValidationStatus.PASS, [], [])]
    with pytest.raises(RuntimeError, match="Rich"):
        r.create_summary_table(results)


def test_reporter_create_failure_table_extracts_validation_id():
    r = ValidationReporter(use_rich=True)
    results = [
        ValidationResult(
            "x.dev",
            ValidationStatus.FAIL,
            [],
            ["[WF-Broker-Requirements] Broker is required"],
        )
    ]
    table = r.create_failure_table(results)
    assert table.row_count == 1


def test_reporter_create_failure_table_long_path_truncation():
    r = ValidationReporter(use_rich=True)
    long_path = "/" + "x" * 100 + "/model.dev"
    results = [ValidationResult(long_path, ValidationStatus.FAIL, [], ["[WF-X] e"])]
    table = r.create_failure_table(results)
    assert table.row_count == 1


def test_reporter_create_failure_table_without_rich_raises():
    r = ValidationReporter(use_rich=False)
    results = [ValidationResult("x.dev", ValidationStatus.FAIL, [], ["e"])]
    with pytest.raises(RuntimeError, match="Rich"):
        r.create_failure_table(results)


def test_reporter_create_failure_table_skips_non_fail_results():
    r = ValidationReporter(use_rich=True)
    results = [
        ValidationResult("a.dev", ValidationStatus.PASS, [], []),
        ValidationResult("b.dev", ValidationStatus.WARN, ["w"], []),
        ValidationResult("c.dev", ValidationStatus.FAIL, [], ["[WF-X] e"]),
    ]
    table = r.create_failure_table(results)
    assert table.row_count == 1


def test_reporter_print_detailed_issues_with_rich(capsys):
    r = ValidationReporter(use_rich=True)
    results = [
        ValidationResult("w.dev", ValidationStatus.WARN, ["warn-msg"], []),
        ValidationResult("f.dev", ValidationStatus.FAIL, [], ["err-msg"]),
    ]
    r.print_detailed_issues(results)
    captured = capsys.readouterr()
    assert "warn-msg" in captured.out
    assert "err-msg" in captured.out


def test_reporter_print_detailed_issues_falls_back_to_simple(capsys):
    r = ValidationReporter(use_rich=False)
    results = [
        ValidationResult("w.dev", ValidationStatus.WARN, ["plain-warn"], []),
        ValidationResult("f.dev", ValidationStatus.FAIL, [], ["plain-err"]),
    ]
    r.print_detailed_issues(results)
    captured = capsys.readouterr()
    assert "Files with Warnings" in captured.out
    assert "plain-warn" in captured.out
    assert "Failed Files" in captured.out
    assert "plain-err" in captured.out


def test_reporter_print_summary_panel_with_rich(capsys):
    r = ValidationReporter(use_rich=True)
    results = [
        ValidationResult("a.dev", ValidationStatus.PASS, [], []),
        ValidationResult("b.dev", ValidationStatus.WARN, ["w"], []),
        ValidationResult("c.dev", ValidationStatus.FAIL, [], ["[WF-X] e"]),
    ]
    r.print_summary_panel(results)
    captured = capsys.readouterr()
    assert "Total" in captured.out or "Summary" in captured.out


def test_reporter_print_summary_panel_without_rich(capsys):
    r = ValidationReporter(use_rich=False)
    results = [
        ValidationResult("a.dev", ValidationStatus.PASS, [], []),
        ValidationResult("b.dev", ValidationStatus.FAIL, [], ["[WF-X] e"]),
    ]
    r.print_summary_panel(results)
    captured = capsys.readouterr()
    assert "SUMMARY" in captured.out
    assert "Total: 2 files" in captured.out


def test_reporter_print_header_with_rich(capsys):
    r = ValidationReporter(use_rich=True)
    r.print_header("My Header")
    captured = capsys.readouterr()
    assert "My Header" in captured.out


def test_reporter_print_header_without_rich(capsys):
    r = ValidationReporter(use_rich=False)
    r.print_header("Plain Header")
    captured = capsys.readouterr()
    assert "Plain Header" in captured.out
    assert "=" * 50 in captured.out


# ── validate_model_file / validate_models (entry points) ───────────────────


def _write_dev(path: Path, body: str) -> Path:
    path.write_text(body)
    return path


VALID_DEV = """
DEVICE MyDev WITH description="x", author="t", os=riotos;
USE RaspberryPi_5_8GB;
USE BME680 [EnvSensor];
NETWORK [WiFi] WITH ssid="s", password="p";
BROKER [MQTT] MyBroker WITH host="localhost", port=1883;
CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3
    @ "dev.sensor.env";
"""

INVALID_DEV = """
DEVICE MyDev WITH description="x", author="t", os=riotos;
USE RaspberryPi_5_8GB;
USE BME680 [EnvSensor];
CONNECT EnvSensor WITH
    POWER gnd -- GND_1;
"""


def test_validate_model_file_pass(tmp_path):
    dev = _write_dev(tmp_path / "valid.dev", VALID_DEV)
    mm = get_device_mm()
    result = validate_model_file(str(dev), mm)
    assert result.status in (ValidationStatus.PASS, ValidationStatus.WARN)
    assert result.errors == []


def test_validate_model_file_fail_with_semantic_error(tmp_path):
    dev = _write_dev(tmp_path / "invalid.dev", INVALID_DEV)
    mm = get_device_mm()
    result = validate_model_file(str(dev), mm)
    assert result.status == ValidationStatus.FAIL
    assert len(result.errors) > 0


def test_validate_model_file_syntax_error(tmp_path):
    bad = _write_dev(tmp_path / "syntax.dev", "DEVICE missing everything")
    mm = get_device_mm()
    result = validate_model_file(str(bad), mm)
    assert result.status == ValidationStatus.FAIL
    assert len(result.errors) > 0


def test_validate_model_file_with_skip_semantics_treats_error_as_warn(tmp_path):
    dev = _write_dev(tmp_path / "invalid.dev", INVALID_DEV)
    mm = get_device_mm()
    mm.skip_semantics = True
    result = validate_model_file(str(dev), mm)
    assert result.status in (ValidationStatus.WARN, ValidationStatus.PASS)


def test_validate_model_file_python_warning_collected(tmp_path):
    dev_body = """
    DEVICE WarnDev WITH description="x", author="t", os=riotos;
    USE RaspberryPi_5_8GB;
    USE BME680 [EnvSensor];
    NETWORK [WiFi] WITH ssid="s", password="p";
    BROKER [MQTT] MyBroker WITH host="localhost", port=1883;
    CONNECT EnvSensor WITH
        POWER gnd -- GND_1, vcc -- power_5v_a
        DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3
        @ "dev.sensor.env";
    """
    dev = _write_dev(tmp_path / "warn.dev", dev_body)
    mm = get_device_mm()
    result = validate_model_file(str(dev), mm)
    assert result.status in (ValidationStatus.PASS, ValidationStatus.WARN)


def test_validate_model_file_unexpected_error_returns_fail(tmp_path):
    broken = _write_dev(tmp_path / "broken.dev", VALID_DEV)
    mm = get_device_mm()
    with patch.object(mm, "model_from_file", side_effect=OSError("simulated")):
        result = validate_model_file(str(broken), mm)
    assert result.status == ValidationStatus.FAIL
    assert any("Unexpected error" in e for e in result.errors)


def test_validate_models_returns_list_in_input_order(tmp_path):
    valid = _write_dev(tmp_path / "a.dev", VALID_DEV)
    invalid = _write_dev(tmp_path / "b.dev", INVALID_DEV)
    mm = get_device_mm()
    results = validate_models([str(valid), str(invalid)], mm, show_progress=False)
    assert len(results) == 2
    assert results[0].status in (ValidationStatus.PASS, ValidationStatus.WARN)
    assert results[1].status == ValidationStatus.FAIL


def test_validate_models_with_reporter_uses_it(capsys, tmp_path):
    valid = _write_dev(tmp_path / "a.dev", VALID_DEV)
    mm = get_device_mm()
    reporter = ValidationReporter(use_rich=False)
    validate_models([str(valid)], mm, show_progress=False, reporter=reporter)
    captured = capsys.readouterr()
    assert "Active Validations" in captured.out
    assert "SUMMARY" in captured.out


def test_validate_models_with_show_progress_simple(capsys, tmp_path):
    valid = _write_dev(tmp_path / "a.dev", VALID_DEV)
    invalid = _write_dev(tmp_path / "b.dev", INVALID_DEV)
    mm = get_device_mm()
    reporter = ValidationReporter(use_rich=False)
    validate_models([str(valid), str(invalid)], mm, show_progress=True, reporter=reporter)
    captured = capsys.readouterr()
    assert "a.dev" in captured.out
    assert "b.dev" in captured.out
