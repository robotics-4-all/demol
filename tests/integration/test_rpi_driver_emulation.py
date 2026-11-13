"""L3: generated driver logic against emulated vendor libraries.

The vendor SDKs are replaced with deterministic stand-ins, so the driver's
address selection, register/field mapping and message-shaping code runs for
real without a Raspberry Pi.
"""

from __future__ import annotations

import importlib.util
import sys
import types
import uuid
from pathlib import Path

import pytest

from rpi_harness import broker_clause, generate_rpi

pytestmark = pytest.mark.integration

DUMMY_BROKER = {"host": "127.0.0.1", "port": 1883}


class _ConstModule(types.ModuleType):
    def __getattr__(self, item):
        if item.startswith("__"):
            raise AttributeError(item)
        return 1


def _module(name: str, **attributes) -> types.ModuleType:
    module = _ConstModule(name)
    module.__path__ = []
    for key, value in attributes.items():
        setattr(module, key, value)
    return module


def _load_driver(out_dir: Path, module_file: str):
    sys.path.insert(0, str(out_dir))
    try:
        spec = importlib.util.spec_from_file_location(f"demol_driver_{uuid.uuid4().hex}", out_dir / module_file)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(out_dir))
        sys.modules.pop("peripheral", None)
        sys.modules.pop("msg", None)
    return module


def _generate(device_mm, tmp_path, name, peripheral_use, connect_block, extra=""):
    model = tmp_path / f"{name}.dev"
    model.write_text(
        f'DEVICE {name} WITH description="emulated", author="demol", os=raspbian;\n'
        f"USE RaspberryPi_4B_4GB;\n"
        f"USE {peripheral_use};\n"
        'NETWORK[WiFi] WITH ssid="n", password="p";\n'
        f"BROKER[MQTT] Local WITH {broker_clause(**DUMMY_BROKER)};\n"
        f"{connect_block}\n"
        f"{extra}\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / f"{name}_out"
    generate_rpi(device_mm, model, out_dir)
    return out_dir


def test_bme680_driver_maps_vendor_fields(device_mm, tmp_path, monkeypatch):
    out_dir = _generate(
        device_mm,
        tmp_path,
        "Bme680Emu",
        "BME680[EnvSensor]",
        "CONNECT EnvSensor WITH\n"
        "    POWER gnd -- GND_1, vcc -- power_5v_a\n"
        "    DATA i2c[slave_address=0x76] sda sda -- GPIO2, scl scl -- GPIO3\n"
        '    @ "sensors/environment";',
    )

    class FakeBme680:
        def __init__(self, address=0x76):
            self.address = address
            self.data = types.SimpleNamespace(
                temperature=21.5,
                pressure=1009.25,
                humidity=44.5,
                gas_resistance=33333.0,
                heat_stable=True,
            )

        def get_sensor_data(self):
            return True

        def __getattr__(self, item):
            return lambda *args, **kwargs: None

    monkeypatch.setitem(sys.modules, "bme680", _module("bme680", BME680=FakeBme680))

    module = _load_driver(out_dir, "bme680_envsensor.py")
    driver = module.BME680_EnvSensor()
    driver.initialize()
    driver.read()

    data = driver.current_state["data"]
    assert data["temperature"] == pytest.approx(21.5)
    assert data["pressure"] == pytest.approx(1009.25)
    assert data["humidity"] == pytest.approx(44.5)
    assert data["gas_resistance"] == pytest.approx(33333.0)


def test_ina219_driver_maps_vendor_fields(device_mm, tmp_path, monkeypatch):
    out_dir = _generate(
        device_mm,
        tmp_path,
        "Ina219Emu",
        "INA219[PowerMonitor]",
        "CONNECT PowerMonitor WITH\n"
        "    POWER GND -- GND_1, VCC -- power_3v3_a\n"
        "    DATA i2c[slave_address=0x40] sda sda -- GPIO2, scl scl -- GPIO3\n"
        '    @ "sensors/power";',
    )

    class FakeIna219:
        def __init__(self, i2c, addr=0x40):
            self.addr = addr
            self.bus_voltage = 5.02
            self.shunt_voltage = 0.012
            self.current = 0.12
            self.power = 0.61

        def set_calibration_32V_2A(self):
            pass

    monkeypatch.setitem(sys.modules, "board", _module("board", SCL=object(), SDA=object()))
    monkeypatch.setitem(sys.modules, "busio", _module("busio", I2C=lambda *a, **k: object()))
    monkeypatch.setitem(
        sys.modules,
        "adafruit_ina219",
        _module("adafruit_ina219", INA219=FakeIna219, ADCResolution=1, BusVoltageRange=1),
    )

    module = _load_driver(out_dir, "ina219_powermonitor.py")
    driver = module.INA219_PowerMonitor()
    driver.initialize()
    driver.read()

    data = driver.current_state["data"]
    assert data["bus_voltage"] == pytest.approx(5.02)
    assert data["shunt_voltage"] == pytest.approx(0.012)
    assert data["current"] == pytest.approx(0.12)
    assert data["power"] == pytest.approx(0.61)


def test_ads1115_driver_maps_all_channels(device_mm, tmp_path, monkeypatch):
    out_dir = _generate(
        device_mm,
        tmp_path,
        "Ads1115Emu",
        "ADS1115[Adc]",
        "CONNECT Adc WITH\n"
        "    POWER GND -- GND_1, VCC -- power_3v3_a\n"
        "    DATA i2c[slave_address=0x48] sda sda -- GPIO2, scl scl -- GPIO3\n"
        '    @ "sensors/adc";',
    )

    class FakeAds1115:
        P0, P1, P2, P3 = 0, 1, 2, 3

        def __init__(self, i2c, address=0x48, gain=1):
            self.address = address
            self.gain = gain

    class FakeAnalogIn:
        def __init__(self, ads, pin):
            self.pin = pin

        @property
        def value(self):
            return 1000 * (self.pin + 1)

        @property
        def voltage(self):
            return 0.5 * (self.pin + 1)

    ads_pkg = _module("adafruit_ads1x15")
    ads_mod = _module("adafruit_ads1x15.ads1115", ADS1115=FakeAds1115, P0=0, P1=1, P2=2, P3=3)
    analog_mod = _module("adafruit_ads1x15.analog_in", AnalogIn=FakeAnalogIn)
    ads_pkg.ads1115 = ads_mod
    ads_pkg.analog_in = analog_mod
    monkeypatch.setitem(sys.modules, "adafruit_ads1x15", ads_pkg)
    monkeypatch.setitem(sys.modules, "adafruit_ads1x15.ads1115", ads_mod)
    monkeypatch.setitem(sys.modules, "adafruit_ads1x15.analog_in", analog_mod)
    monkeypatch.setitem(sys.modules, "board", _module("board", SCL=object(), SDA=object()))
    monkeypatch.setitem(sys.modules, "busio", _module("busio", I2C=lambda *a, **k: object()))

    module = _load_driver(out_dir, "ads1115_adc.py")
    driver = module.ADS1115_Adc()
    driver.initialize()
    driver.read()

    data = driver.current_state["data"]
    for channel in range(4):
        assert data[f"channel_{channel}_value"] == pytest.approx(1000 * (channel + 1))
        assert data[f"channel_{channel}_voltage"] == pytest.approx(0.5 * (channel + 1))
