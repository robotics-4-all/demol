"""Unit tests for the shared PeripheralTemplateMapper.

Covers the unified ``get_template(peripheral_ref, os_name)`` method that
returns the raw template string for a peripheral on a given target OS,
plus the RIOT caller's local ``_strip_riot_template_suffix`` helper that
turns the raw string into the peripheral base name used for driver
filenames (``sensor_<base>_N.c``). Also re-verifies the
backward-compat re-exports from ``m2t_rpi`` / ``m2t_riot``.
"""

from types import SimpleNamespace

from demol.transformations._template_mapper import PeripheralTemplateMapper
from demol.transformations.m2t_riot import _strip_riot_template_suffix


def _make_peripheral_ref(name, templates):
    """Helper: build a minimal peripheral_ref with .name and .templates."""
    return SimpleNamespace(name=name, templates=templates)


def _make_template_mapping(os_name, template):
    return SimpleNamespace(os=os_name, template=template)


def test_get_template_raspbian_returns_full_filename():
    """RPi behavior: get_template returns the full template filename for raspbian."""
    peripheral_ref = _make_peripheral_ref("bme680", [_make_template_mapping("raspbian", "bme680.py.tmpl")])
    result = PeripheralTemplateMapper.get_template(peripheral_ref, "raspbian")
    assert result == "bme680.py.tmpl"


def test_get_template_unknown_returns_none(caplog):
    """RPi behavior: get_template returns None if no raspbian template."""
    peripheral_ref = _make_peripheral_ref("xyz", [_make_template_mapping("riotos", "xyz.c.j2")])
    with caplog.at_level("WARNING"):
        result = PeripheralTemplateMapper.get_template(peripheral_ref, "raspbian")
    assert result is None


def test_get_template_riotos_returns_raw_string_and_stripper_strips_cj2():
    """RiotOS behavior: get_template returns the raw .c.j2 string; stripper returns the base name."""
    peripheral_ref = _make_peripheral_ref("bme680", [_make_template_mapping("riotos", "bme680.c.j2")])
    raw = PeripheralTemplateMapper.get_template(peripheral_ref, "riotos")
    assert raw == "bme680.c.j2"
    assert _strip_riot_template_suffix(raw) == "bme680"


def test_get_template_riotos_returns_raw_string_and_stripper_strips_j2_and_riot_suffix():
    """RiotOS behavior: get_template returns the raw .j2 string; stripper handles _riot suffix."""
    peripheral_ref = _make_peripheral_ref("led", [_make_template_mapping("riotos", "ws281x_riot.j2")])
    raw = PeripheralTemplateMapper.get_template(peripheral_ref, "riotos")
    assert raw == "ws281x_riot.j2"
    assert _strip_riot_template_suffix(raw) == "ws281x"


def test_get_template_riotos_no_template_returns_none(caplog):
    """RiotOS behavior: returns None if no riotos template is declared."""
    peripheral_ref = _make_peripheral_ref("xyz", [_make_template_mapping("raspbian", "xyz.py.tmpl")])
    with caplog.at_level("WARNING"):
        result = PeripheralTemplateMapper.get_template(peripheral_ref, "riotos")
    assert result is None


def test_backward_compat_import_from_m2t_rpi():
    """Backward-compat: PeripheralTemplateMapper still importable from m2t_rpi."""
    from demol.transformations.m2t_rpi import PeripheralTemplateMapper as RPiMapper

    assert RPiMapper is PeripheralTemplateMapper


def test_backward_compat_import_from_m2t_riot():
    """Backward-compat: PeripheralTemplateMapper still importable from m2t_riot."""
    from demol.transformations.m2t_riot import PeripheralTemplateMapper as RiotMapper

    assert RiotMapper is PeripheralTemplateMapper
