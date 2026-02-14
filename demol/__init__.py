from textx import language

from demol.lang import (
    get_component_mm,
    get_device_mm,
)


@language("demol-component", "*.hwd")
def component_language():
    return get_component_mm()


@language("demol-device", "*.dev")
def device_language():
    return get_device_mm()
