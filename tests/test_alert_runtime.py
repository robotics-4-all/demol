"""Runtime contract tests for the generated ``alerts.py`` module.

Loads the actual rendered template, instantiates ``AlertTrigger`` with mock
condition + action callables, and verifies:
  - Conditions that return False do not fire actions
  - Conditions that return True fire all actions
  - Cooldown blocks repeat firings within the window and re-allows after
  - Condition errors (KeyError/TypeError/ValueError) become no-fires, not raises
  - Action exceptions are swallowed and do not abort sibling actions
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from demol.transformations.m2t_rpi import RPiCodeGenerator


def _load_generated_alerts(out_dir: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("_generated_alerts", out_dir / "alerts.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_generated_alerts"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def alerts_module(device_mm, tmp_path_factory):
    out = tmp_path_factory.mktemp("alerts_runtime")
    model = device_mm.model_from_file("examples/rpi/rpi_health_monitor.dev")
    RPiCodeGenerator(model, out).generate()
    return _load_generated_alerts(out)


class TestAlertTriggerBasic:
    def test_false_condition_does_not_fire(self, alerts_module):
        calls = []
        trig = alerts_module.AlertTrigger(
            name="t1",
            condition=lambda data: False,
            actions=[lambda: calls.append("a")],
            cooldown_sec=0.0,
        )
        assert trig.evaluate({"x": 1}) is False
        assert calls == []

    def test_true_condition_fires_all_actions(self, alerts_module):
        calls = []
        trig = alerts_module.AlertTrigger(
            name="t1",
            condition=lambda data: data["x"] > 5,
            actions=[lambda: calls.append("a"), lambda: calls.append("b")],
            cooldown_sec=0.0,
        )
        assert trig.evaluate({"x": 10}) is True
        assert calls == ["a", "b"]


class TestCooldown:
    def test_cooldown_blocks_repeat_within_window(self, alerts_module):
        calls = []
        trig = alerts_module.AlertTrigger(
            name="t1",
            condition=lambda data: True,
            actions=[lambda: calls.append("a")],
            cooldown_sec=10.0,
        )
        assert trig.evaluate({}) is True
        assert trig.evaluate({}) is False
        assert trig.evaluate({}) is False
        assert calls == ["a"]

    def test_cooldown_zero_allows_immediate_refire(self, alerts_module):
        calls = []
        trig = alerts_module.AlertTrigger(
            name="t1",
            condition=lambda data: True,
            actions=[lambda: calls.append("a")],
            cooldown_sec=0.0,
        )
        assert trig.evaluate({}) is True
        assert trig.evaluate({}) is True
        assert calls == ["a", "a"]

    def test_cooldown_re_allows_after_window(self, alerts_module, monkeypatch):
        calls = []
        clock = {"t": 1000.0}
        monkeypatch.setattr(alerts_module.time, "monotonic", lambda: clock["t"])
        trig = alerts_module.AlertTrigger(
            name="t1",
            condition=lambda data: True,
            actions=[lambda: calls.append("a")],
            cooldown_sec=5.0,
        )
        assert trig.evaluate({}) is True
        clock["t"] += 2.0
        assert trig.evaluate({}) is False
        clock["t"] += 4.0
        assert trig.evaluate({}) is True
        assert calls == ["a", "a"]


class TestErrorIsolation:
    @pytest.mark.parametrize("exc", [KeyError("x"), TypeError("bad"), ValueError("nope")])
    def test_condition_errors_are_no_fires(self, alerts_module, exc):
        def boom(_data):
            raise exc

        calls = []
        trig = alerts_module.AlertTrigger(
            name="t1",
            condition=boom,
            actions=[lambda: calls.append("a")],
            cooldown_sec=0.0,
        )
        assert trig.evaluate({}) is False
        assert calls == []

    def test_action_exception_does_not_abort_siblings(self, alerts_module):
        calls = []

        def bad():
            raise RuntimeError("publisher down")

        trig = alerts_module.AlertTrigger(
            name="t1",
            condition=lambda data: True,
            actions=[bad, lambda: calls.append("after")],
            cooldown_sec=0.0,
        )
        assert trig.evaluate({}) is True
        assert calls == ["after"]
