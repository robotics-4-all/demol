from textx.exceptions import TextXSemanticError
import pytest

def test_valid_sensor(component_mm):
    model_str = """
    SENSOR[Env] MySensor WITH
        OP
            vcc=3V3,
            power.min=10 mW,
            power.max=20 mW,
            power.avg=15 mW
        PINS
            p1[3V3] @ 1,
            p2[GND] @ 2,
            p3[gpio] @ 3
    ;
    """
    model = component_mm.model_from_str(model_str)
    assert model.component.name == "MySensor"
    assert model.component.operational.vcc == "3V3"

def test_valid_actuator(component_mm):
    model_str = """
    ACTUATOR[Relay] MyRelay WITH
        OP
            vcc=5V,
            power.min=5 mW,
            power.max=10 mW,
            power.avg=7 mW
        PINS
            p1[5V] @ 1,
            p2[GND] @ 2
    ;
    """
    model = component_mm.model_from_str(model_str)
    assert model.component.name == "MyRelay"

def test_sensor_attributes(component_mm):
    model_str = """
    SENSOR[Env] AttrSensor WITH
        OP
            vcc=3V3
        PINS
            p1[gpio] @ 1
        ATTRIBUTES
            poll_period[int] = 100,
            name[str] = "test_sensor",
            enabled[bool] = true
    ;
    """
    model = component_mm.model_from_str(model_str)
    attrs = {a.name: a.default for a in model.component.attributes}
    assert attrs['poll_period'] == 100
    assert attrs['name'] == "test_sensor"
    assert attrs['enabled'] is True

def test_sensor_templates(component_mm):
    model_str = """
    SENSOR[Env] TmplSensor WITH
        OP
            vcc=3V3
        PINS
            p1[gpio] @ 1
        TEMPLATES
            raspbian="sensor.py.tmpl",
            riotos="sensor.c.tmpl"
    ;
    """
    model = component_mm.model_from_str(model_str)
    tmpls = {t.os: t.template for t in model.component.templates}
    assert tmpls['raspbian'] == "sensor.py.tmpl"
    assert tmpls['riotos'] == "sensor.c.tmpl"

def test_invalid_syntax_missing_semicolon(component_mm):
    model_str = """
    SENSOR[Env] BadSensor WITH
        OP vcc=3V3
        PINS p1[gpio] @ 1
    """
    with pytest.raises(Exception): # Syntax error
        component_mm.model_from_str(model_str)
