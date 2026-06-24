"""Tests for BoardNameRegistry and the Zephyr-side Kconfig / devicetree
rendering pipeline introduced in Task 2.2 of the multi-backend evolution.

The tests cover three concerns:

* ``BoardNameRegistry`` lookups for the boards shipped with DeMoL and
  the legacy ``RaspberryPi_4_Model_B`` alias.
* End-to-end Zephyr code generation on ``examples/esp/esp_iot_device.dev``,
  asserting that ``prj.conf`` exposes the BME680 Kconfig symbol and the
  devicetree overlay contains the I2C node.
* The end-to-end CLI invocation from the task spec.
"""

from pathlib import Path

import pytest

from demol.transformations.board_registry import BoardNameRegistry
from demol.transformations.m2t_zephyr import ZephyrCodeGenerator, m2t_zephyr


# ---------------------------------------------------------------------------
# BoardNameRegistry unit tests
# ---------------------------------------------------------------------------


def test_registry_resolve_rpi4_legacy_to_zephyr():
    """Legacy ``RaspberryPi_4_Model_B`` maps to ``rpi_4b`` on Zephyr."""
    reg = BoardNameRegistry()
    assert reg.resolve("RaspberryPi_4_Model_B", "zephyr") == "rpi_4b"


def test_registry_resolve_esp32_riotos():
    """ESP32 maps to ``esp32-wroom-32`` on RIOT OS (lowercase input)."""
    reg = BoardNameRegistry()
    assert reg.resolve("esp32wroom32", "riotos") == "esp32-wroom-32"


def test_registry_resolve_is_case_insensitive():
    """``resolve`` normalizes board names to lowercase."""
    reg = BoardNameRegistry()
    assert reg.resolve("ESP32Wroom32", "zephyr") == "esp32_devkitc"
    assert reg.resolve("eSp32wROOM32", "zephyr") == "esp32_devkitc"


def test_registry_resolve_rpi4b_4gb_aliased_to_rpi4b():
    """``RaspberryPi_4B_4GB`` (current DeMoL board) → ``rpi_4b``."""
    reg = BoardNameRegistry()
    assert reg.resolve("RaspberryPi_4B_4GB", "zephyr") == "rpi_4b"
    assert reg.resolve("RaspberryPi_4B_8GB", "zephyr") == "rpi_4b"


def test_registry_resolve_rpi5():
    """RaspberryPi 5 maps to ``rpi_5`` on Zephyr."""
    reg = BoardNameRegistry()
    assert reg.resolve("RaspberryPi_5_8GB", "zephyr") == "rpi_5"


def test_registry_resolve_unknown_falls_back_to_lowercased_name():
    """Unknown boards fall back to the lowercased DeMoL name (no error)."""
    reg = BoardNameRegistry()
    assert reg.resolve("CustomBoard_42", "zephyr") == "customboard_42"
    assert reg.resolve("CustomBoard_42", "riotos") == "customboard_42"


def test_registry_get_returns_none_for_unknown():
    """``get`` returns ``None`` for unmapped pairs, distinct from ``resolve``."""
    reg = BoardNameRegistry()
    assert reg.get("CustomBoard_42", "zephyr") is None
    assert reg.get("RaspberryPi_4_Model_B", "zephyr") == "rpi_4b"


def test_registry_register_new_mapping():
    """``register`` adds a custom mapping that is then resolvable."""
    reg = BoardNameRegistry()
    reg.register("MyCustomBoard", "zephyr", "my_custom_target")
    assert reg.resolve("MyCustomBoard", "zephyr") == "my_custom_target"


def test_registry_register_rejects_duplicate_by_default():
    """Double-registering the same pair raises ``ValueError``."""
    reg = BoardNameRegistry()
    reg.register("DupBoard", "zephyr", "target_a")
    with pytest.raises(ValueError, match="duplicate mapping"):
        reg.register("DupBoard", "zephyr", "target_b")


def test_registry_register_overwrite_replaces():
    """``overwrite=True`` allows replacing an existing mapping."""
    reg = BoardNameRegistry()
    reg.register("DupBoard", "zephyr", "target_a")
    reg.register("DupBoard", "zephyr", "target_b", overwrite=True)
    assert reg.resolve("DupBoard", "zephyr") == "target_b"


def test_registry_known_boards_lists_registered_keys():
    """``known_boards`` returns the registered (lowercased) board names."""
    reg = BoardNameRegistry()
    known = reg.known_boards()
    assert "raspberrypi_4_model_b" in known
    assert "esp32wroom32" in known


def test_registry_contains():
    """``in`` operator works on the registry for membership checks."""
    reg = BoardNameRegistry()
    assert "RaspberryPi_4_Model_B" in reg
    assert "esp32wroom32" in reg
    assert "NotARealBoard" not in reg


def test_registry_mutation_is_isolated_between_instances():
    """Mutations on one instance do not leak into a fresh instance."""
    a = BoardNameRegistry()
    a.register("IsolatedBoard", "zephyr", "iso_target")
    b = BoardNameRegistry()
    assert "IsolatedBoard" not in b


# ---------------------------------------------------------------------------
# Zephyr code-generation end-to-end tests
# ---------------------------------------------------------------------------


def test_zephyr_codegen_emits_kconfig_with_bme680(tmp_path, device_mm):
    """``prj.conf`` for the ESP IoT example contains ``CONFIG_BME680=y``."""
    model = device_mm.model_from_file(
        str(Path("examples/esp/esp_iot_device.dev").resolve())
    )
    gen = ZephyrCodeGenerator(model, tmp_path)
    gen.generate()

    prj_conf = (tmp_path / "app" / "prj.conf").read_text(encoding="utf-8")
    assert "CONFIG_BME680=y" in prj_conf


def test_zephyr_codegen_emits_devicetree_i2c_node(tmp_path, device_mm):
    """The devicetree overlay contains the BME680 I2C node at ``0x76``."""
    model = device_mm.model_from_file(
        str(Path("examples/esp/esp_iot_device.dev").resolve())
    )
    gen = ZephyrCodeGenerator(model, tmp_path)
    gen.generate()

    overlay_files = list((tmp_path / "app" / "boards").glob("*.overlay"))
    assert overlay_files, "Expected at least one .overlay file"
    overlay = overlay_files[0].read_text(encoding="utf-8")
    assert "bme680@0x76" in overlay
    assert "&i2c0" in overlay
    assert 'compatible = "bosch,bme680"' in overlay


def test_zephyr_codegen_resolves_esp32_to_devkitc(tmp_path, device_mm):
    """The ESP32Wroom32 board resolves to the Zephyr ``esp32_devkitc`` target."""
    model = device_mm.model_from_file(
        str(Path("examples/esp/esp_iot_device.dev").resolve())
    )
    gen = ZephyrCodeGenerator(model, tmp_path)
    assert gen._resolve_board_name() == "esp32_devkitc"


def test_zephyr_codegen_emits_cmakelists(tmp_path, device_mm):
    """The CMakeLists.txt references the resolved board name and src/main.c."""
    model = device_mm.model_from_file(
        str(Path("examples/esp/esp_iot_device.dev").resolve())
    )
    gen = ZephyrCodeGenerator(model, tmp_path)
    gen.generate()

    cmake = (tmp_path / "app" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "project(esp32_devkitc)" in cmake
    assert "target_sources(app PRIVATE src/main.c" in cmake
    assert "target_include_directories(app PRIVATE src/include)" in cmake


def test_zephyr_codegen_board_override_takes_precedence(tmp_path, device_mm):
    """``board_override`` overrides both the registry and the .hwd block."""
    model = device_mm.model_from_file(
        str(Path("examples/esp/esp_iot_device.dev").resolve())
    )
    gen = ZephyrCodeGenerator(
        model, tmp_path, board_override="my_custom_board"
    )
    assert gen._resolve_board_name() == "my_custom_board"


def test_zephyr_codegen_emits_main_c_skeleton(tmp_path, device_mm):
    """The main.c skeleton is emitted with the Zephyr include."""
    model = device_mm.model_from_file(
        str(Path("examples/esp/esp_iot_device.dev").resolve())
    )
    gen = ZephyrCodeGenerator(model, tmp_path)
    gen.generate()

    main_c = (tmp_path / "app" / "src" / "main.c").read_text(encoding="utf-8")
    assert "#include <zephyr/kernel.h>" in main_c
    assert "int main(void)" in main_c


# ---------------------------------------------------------------------------
# Module-level entry point
# ---------------------------------------------------------------------------


def test_m2t_zephyr_function_accepts_board_override(tmp_path, device_mm):
    """The module-level ``m2t_zephyr`` accepts a ``board_override`` keyword."""
    model = device_mm.model_from_file(
        str(Path("examples/esp/esp_iot_device.dev").resolve())
    )
    m2t_zephyr(model, output_dir=tmp_path, board_override="custom_target")
    cmake = (tmp_path / "app" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "project(custom_target)" in cmake
