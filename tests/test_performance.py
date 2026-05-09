"""
Performance benchmarks for parser and validator pipeline.

Measures parse + validate times to detect regressions and establish baselines.
Uses pytest-benchmark style (manual timing) since pytest-benchmark is not a dependency.
"""

import time
import warnings
import pytest
from demol.lang import get_device_mm

pytestmark = pytest.mark.performance


@pytest.fixture(scope="module")
def mm():
    return get_device_mm(skip_semantics=True)


@pytest.fixture(scope="module")
def mm_full():
    return get_device_mm()


SMALL_MODEL = """
DEVICE SmallDevice WITH description="small", author="test", os=raspbian;
USE RaspberryPi_5_8GB;
USE BME680[Sensor1];
NETWORK[WiFi] WITH ssid="net", password="pass";
BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";
CONNECT Sensor1 WITH
    POWER gnd -- GND_1, vcc -- power_5v_a
    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3
    @ "sensors/env";
"""


PERIPHERAL_TYPES = [
    "BME680",
    "ServoGeneric",
    "HCSR04",
    "LedGeneric",
    "SRF04",
    "BuzzerGeneric",
]


def _build_large_model(num_peripherals):
    lines = [
        'DEVICE LargeDevice WITH description="perf test", author="test", os=raspbian;',
        "USE RaspberryPi_5_8GB;",
    ]
    periph_names = []
    for i in range(num_peripherals):
        name = f"P{i}"
        ptype = PERIPHERAL_TYPES[i % len(PERIPHERAL_TYPES)]
        periph_names.append(name)
        lines.append(f"USE {ptype}[{name}];")

    lines.append('NETWORK[WiFi] WITH ssid="net", password="pass";')
    lines.append('BROKER[MQTT] B WITH host="localhost", port=1883, auth.username="u", auth.password="p";')

    for name in periph_names:
        lines.append(f'SMARTCONNECT {name} @ "sensors/{name.lower()}";')

    return "\n".join(lines)


def test_parse_small_model_under_500ms(mm):
    start = time.perf_counter()
    iterations = 5
    for _ in range(iterations):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mm.model_from_str(SMALL_MODEL)
    elapsed = (time.perf_counter() - start) / iterations
    assert elapsed < 0.5, f"Small model parse took {elapsed:.3f}s (limit: 0.5s)"


def test_parse_medium_model_under_1s(mm):
    model_str = _build_large_model(5)
    start = time.perf_counter()
    iterations = 3
    for _ in range(iterations):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mm.model_from_str(model_str)
    elapsed = (time.perf_counter() - start) / iterations
    assert elapsed < 1.0, f"Medium model (5 peripherals) took {elapsed:.3f}s (limit: 1.0s)"


def test_parse_large_model_under_3s(mm):
    model_str = _build_large_model(10)
    start = time.perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mm.model_from_str(model_str)
    elapsed = time.perf_counter() - start
    assert elapsed < 3.0, f"Large model (10 peripherals) took {elapsed:.3f}s (limit: 3.0s)"


def test_full_validation_small_model_under_300ms(mm_full):
    start = time.perf_counter()
    iterations = 3
    for _ in range(iterations):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mm_full.model_from_str(SMALL_MODEL)
    elapsed = (time.perf_counter() - start) / iterations
    assert elapsed < 0.3, f"Full validation took {elapsed:.3f}s (limit: 0.3s)"


def test_metamodel_construction_under_1s():
    start = time.perf_counter()
    get_device_mm()
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"Metamodel construction took {elapsed:.3f}s (limit: 1.0s)"
