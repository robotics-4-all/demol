"""Unit tests for the shared PeripheralTemplateMapper.

Covers both get_template (RPi/raspbian behavior) and get_template_base
(RiotOS behavior) methods, plus backward-compat re-exports.
"""
from types import SimpleNamespace

from demol.transformations._template_mapper import PeripheralTemplateMapper


def _make_peripheral_ref(name, templates):
    """Helper: build a minimal peripheral_ref with .name and .templates."""
    return SimpleNamespace(name=name, templates=templates)


def _make_template_mapping(os_name, template):
    return SimpleNamespace(os=os_name, template=template)


def test_get_template_raspbian_returns_full_filename():
    """RPi behavior: get_template returns the full template filename."""
    peripheral_ref = _make_peripheral_ref(
        "bme680", [_make_template_mapping("raspbian", "bme680.py.tmpl")]
    )
    result = PeripheralTemplateMapper.get_template(peripheral_ref)
    assert result == "bme680.py.tmpl"


def test_get_template_unknown_returns_none(caplog):
    """RPi behavior: get_template returns None if no raspbian template."""
    peripheral_ref = _make_peripheral_ref(
        "xyz", [_make_template_mapping("riotos", "xyz.c.j2")]
    )
    with caplog.at_level("WARNING"):
        result = PeripheralTemplateMapper.get_template(peripheral_ref)
    assert result is None


def test_get_template_base_riotos_strips_cj2():
    """RiotOS behavior: get_template_base strips .c.j2 suffix."""
    peripheral_ref = _make_peripheral_ref(
        "bme680", [_make_template_mapping("riotos", "bme680.c.j2")]
    )
    result = PeripheralTemplateMapper.get_template_base(peripheral_ref)
    assert result == "bme680"


def test_get_template_base_riotos_strips_j2_and_riot_suffix():
    """RiotOS behavior: get_template_base strips .j2 and _riot suffix."""
    peripheral_ref = _make_peripheral_ref(
        "led", [_make_template_mapping("riotos", "ws281x_riot.j2")]
    )
    result = PeripheralTemplateMapper.get_template_base(peripheral_ref)
    assert result == "ws281x"


def test_get_template_base_riotos_no_template_returns_none():
    """RiotOS behavior: returns None if no riotos template (silent, not warning)."""
    peripheral_ref = _make_peripheral_ref(
        "xyz", [_make_template_mapping("raspbian", "xyz.py.tmpl")]
    )
    result = PeripheralTemplateMapper.get_template_base(peripheral_ref)
    assert result is None


def test_backward_compat_import_from_m2t_rpi():
    """Backward-compat: PeripheralTemplateMapper still importable from m2t_rpi."""
    from demol.transformations.m2t_rpi import PeripheralTemplateMapper as RPiMapper

    assert RPiMapper is PeripheralTemplateMapper


def test_backward_compat_import_from_m2t_riot():
    """Backward-compat: PeripheralTemplateMapper still importable from m2t_riot."""
    from demol.transformations.m2t_riot import PeripheralTemplateMapper as RiotMapper

    assert RiotMapper is PeripheralTemplateMapper
