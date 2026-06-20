"""End-to-end CLI tests using Click's CliRunner.

Exercises every public command of the `demol` group via CliRunner. This
catches dispatch and argument-parsing regressions that unit tests on
backend functions would miss (e.g. the esp_iot_device.dev parse bug
that escaped the test suite until CI's riot-build step found it).
"""
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from demol.cli.cli import cli
from demol.lang.device import get_device_mm


VALID_DEV = """
DEVICE CliDev WITH description="x", author="t", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680 [EnvSensor];
NETWORK [WiFi] WITH ssid="s", password="p";
BROKER [MQTT] MyBroker WITH host="localhost", port=1883;
CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c [slave_address=0x77] sda sda -- GPIO2, scl scl -- GPIO3
    @ "dev.sensor.env";
"""


def _build_model():
    mm = get_device_mm()
    mm.skip_semantics = True
    return mm.model_from_str(VALID_DEV)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def valid_dev(tmp_path):
    p = tmp_path / "valid.dev"
    p.write_text(VALID_DEV)
    return p


def test_cli_help_runs(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "DeMoL" in result.output


def test_validate_command_exits_nonzero_on_missing_file(runner, tmp_path):
    result = runner.invoke(cli, ["validate", str(tmp_path / "missing.dev")])
    assert result.exit_code != 0


def test_generate_rpi_creates_files(runner, valid_dev, tmp_path):
    out = tmp_path / "rpi_out"
    with patch("demol.cli.cli.build_model", side_effect=lambda *a, **kw: _build_model()):
        result = runner.invoke(cli, ["generate", "rpi", str(valid_dev), "--output-dir", str(out)])
    assert result.exit_code == 0
    assert out.exists()


def test_generate_docs_creates_files(runner, valid_dev, tmp_path):
    out = tmp_path / "docs_out"
    with patch("demol.cli.cli.build_model", side_effect=lambda *a, **kw: _build_model()):
        result = runner.invoke(cli, ["generate", "docs", str(valid_dev), "--output-dir", str(out)])
    assert result.exit_code == 0
    assert out.exists()


def test_generate_json_creates_file(runner, valid_dev, tmp_path):
    out = tmp_path / "json_out"
    out.mkdir()
    with patch("demol.cli.cli.build_model", side_effect=lambda *a, **kw: _build_model()):
        result = runner.invoke(cli, ["generate", "json", str(valid_dev), "--output-dir", str(out)])
    assert result.exit_code == 0
    assert (out / "CliDev.json").exists()


def test_generate_pinmap_creates_files(runner, valid_dev, tmp_path):
    out = tmp_path / "pinmap_out"
    with patch("demol.cli.cli.build_model", side_effect=lambda *a, **kw: _build_model()):
        result = runner.invoke(cli, ["generate", "pinmap", str(valid_dev), "--output-dir", str(out)])
    assert result.exit_code == 0
    assert (out / "CliDev_pinmap.md").exists()
    assert (out / "CliDev_pinmap.json").exists()


def test_generate_svg_creates_file(runner, valid_dev, tmp_path):
    out = tmp_path / "svg_out"
    with patch("demol.cli.cli.build_model", side_effect=lambda *a, **kw: _build_model()):
        result = runner.invoke(cli, ["generate", "svg", str(valid_dev), "--output-dir", str(out)])
    assert result.exit_code == 0
    assert (out / "CliDev.svg").exists()


def test_generate_svg_infrastructure_creates_file(runner, valid_dev, tmp_path):
    out = tmp_path / "svg_out"
    with patch("demol.cli.cli.build_model", side_effect=lambda *a, **kw: _build_model()):
        result = runner.invoke(cli, ["generate", "svg", str(valid_dev), "--output-dir", str(out), "--infrastructure"])
    assert result.exit_code == 0
    assert (out / "CliDev_infrastructure.svg").exists()


def test_generate_smauto_creates_files(runner, valid_dev, tmp_path):
    out = tmp_path / "smauto_out"
    with patch("demol.cli.cli.build_model", side_effect=lambda *a, **kw: _build_model()):
        result = runner.invoke(cli, ["generate", "smauto", str(valid_dev), "--output-dir", str(out)])
    assert result.exit_code == 0


def test_fix_command_dry_run(runner, valid_dev):
    result = runner.invoke(cli, ["fix", str(valid_dev), "--dry-run"])
    assert result.exit_code == 0


def test_fix_command_exits_nonzero_on_missing_file(runner, tmp_path):
    result = runner.invoke(cli, ["fix", str(tmp_path / "missing.dev")])
    assert result.exit_code != 0


def test_diff_command_on_identical_models(runner, tmp_path):
    p1 = tmp_path / "a.dev"
    p2 = tmp_path / "b.dev"
    p1.write_text(VALID_DEV)
    p2.write_text(VALID_DEV)
    result = runner.invoke(cli, ["diff", str(p1), str(p2)])
    assert result.exit_code == 0
    assert "semantically identical" in result.output.lower()


def test_diff_command_exits_nonzero_on_missing_file(runner, tmp_path):
    p1 = tmp_path / "a.dev"
    p1.write_text(VALID_DEV)
    result = runner.invoke(cli, ["diff", str(p1), str(tmp_path / "missing.dev")])
    assert result.exit_code != 0


def test_generate_help_lists_all_subcommands(runner):
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    for sub in ["rpi", "riot", "docs", "svg", "json", "smauto", "pinmap"]:
        assert sub in result.output


def test_analyze_help_shows_power_subcommand(runner):
    result = runner.invoke(cli, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "power" in result.output
