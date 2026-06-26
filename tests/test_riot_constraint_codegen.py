"""String-level emission tests for CONSTRAINT codegen on the RiotOS target.

Covers the contract documented in ``docs/constraint-runtime-design.md`` section 3:
- ``constraint.c`` and ``constraint.h`` are emitted when ``model.constraints`` is
  non-empty, and skipped otherwise (backward compat).
- ``constraint.c`` defines ``check_constraints()`` plus the built-in helpers
  (``count_sensors``, ``count_actuators``, ``count_peripherals``, ``sum_power_mW``,
  ``max_power_mW``, ``count_connected``).
- ``constraint.h`` declares the runtime state struct and the public prototypes.
- The generated ``Makefile`` references ``constraint.c`` so RIOT compiles it.
- Re-generation of the same model is byte-identical.
"""

from pathlib import Path

from demol.lang.device import get_device_mm

from demol.transformations.m2t_riot import m2t_riot

BASE_MODEL = """
DEVICE ConstraintTest WITH
    description="Constraint test",
    author="tester",
    os=riotos;

USE ESP32Wroom32;
USE BME680 [EnvSensor];
USE LedGeneric [StatusLed];

NETWORK [WiFi] WITH ssid="ssid", password="pass";

BROKER [MQTT] MyBroker WITH
    host="localhost",
    port=1883;

CONNECT EnvSensor WITH
    POWER gnd -- GND_1, vcc -- VCC_5V
    DATA i2c[slave_address=0x77] sda sda -- GPIO21, scl scl -- GPIO22;


CONNECT StatusLed WITH
    POWER gnd -- GND_1, vcc -- VCC_3V3
    DATA gpio[mode="output"] vin -- GPIO18;
"""


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _generate(model_str: str, out: Path) -> None:
    mm = get_device_mm()
    model = mm.model_from_str(model_str)
    m2t_riot(model, output_dir=str(out))


class TestConstraintFileEmission:
    def test_constraint_codegen_emits_files(self, tmp_path):
        model_str = BASE_MODEL + """
        CONSTRAINT min_sensors: count(SENSOR) >= 1;
        """
        out = tmp_path / "out"
        _generate(model_str, out)
        assert (out / "constraint.c").exists()
        assert (out / "constraint.h").exists()

    def test_constraint_codegen_skips_when_no_constraints(self, tmp_path):
        out = tmp_path / "out"
        _generate(BASE_MODEL, out)
        assert not (out / "constraint.c").exists()
        assert not (out / "constraint.h").exists()


class TestConstraintCSymbols:
    def test_generated_constraint_c_has_check_function(self, tmp_path):
        model_str = BASE_MODEL + """
        CONSTRAINT min_sensors: count(SENSOR) >= 1;
        """
        out = tmp_path / "out"
        _generate(model_str, out)
        body = _read(out / "constraint.c")
        assert "void check_constraints" in body

    def test_generated_constraint_c_has_helpers(self, tmp_path):
        model_str = BASE_MODEL + """
        CONSTRAINT min_sensors: count(SENSOR) >= 1;
        CONSTRAINT budget: sum_power(PERIPHERAL) < 5000 mW;
        """
        out = tmp_path / "out"
        _generate(model_str, out)
        body = _read(out / "constraint.c")
        assert "int count_sensors" in body
        assert "int count_actuators" in body
        assert "int count_peripherals" in body
        assert "int sum_power_mW" in body
        assert "int max_power_mW" in body


class TestConstraintHStructure:
    def test_generated_constraint_h_has_struct(self, tmp_path):
        model_str = BASE_MODEL + """
        CONSTRAINT min_sensors: count(SENSOR) >= 1;
        """
        out = tmp_path / "out"
        _generate(model_str, out)
        body = _read(out / "constraint.h")
        # Expect a typedef struct and a state declaration
        assert "typedef struct" in body
        assert "constraint_state" in body
        # Public prototypes
        assert "void check_constraints" in body


class TestMakefileIntegration:
    def test_makefile_includes_constraint(self, tmp_path):
        model_str = BASE_MODEL + """
        CONSTRAINT min_sensors: count(SENSOR) >= 1;
        """
        out = tmp_path / "out"
        _generate(model_str, out)
        body = _read(out / "Makefile")
        assert "constraint.c" in body


class TestRegeneration:
    def test_constraint_codegen_byte_identical_regen(self, tmp_path):
        model_str = BASE_MODEL + """
        CONSTRAINT min_sensors: count(SENSOR) >= 1;
        CONSTRAINT budget: sum_power(PERIPHERAL) < 5000 mW;
        """
        out1 = tmp_path / "out1"
        out2 = tmp_path / "out2"
        _generate(model_str, out1)
        _generate(model_str, out2)
        for f in ("constraint.c", "constraint.h", "Makefile"):
            a = (out1 / f).read_bytes()
            b = (out2 / f).read_bytes()
            assert a == b, f"{f} differs between regenerations"
