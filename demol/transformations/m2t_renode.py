"""Model-to-Text transformation for Renode simulation projects.

This module transforms DeMoL device models into a Renode simulation project.
Renode (https://renode.io) is an instruction-set simulator primarily used
for embedded / IoT firmware bring-up; the generated project is a minimal
``.repl`` script plus a ``test_device.py`` driver that uses ``pyrenode3``
to spawn the simulator in-process and load the script.

The generator emits two artifacts at the project root:

* ``device.repl``     — Renode platform description + machine load script.
* ``test_device.py`` — pytest-style driver that boots the REPL via
                       ``pyrenode3.Antmicro`` and asserts the machine loads.

Both files are rendered through the Jinja2 templates in
``demol/templates/renode/`` (``repl.j2``, ``test_script.py.j2``). No Renode
installation or network call is required for generation to succeed; the
generated ``test_device.py`` only needs ``pyrenode3`` at test-run time.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import jinja2

from demol.definitions import TEMPLATES_RENODE
from .base_generator import BaseCodeGenerator
from .board_registry import BoardNameRegistry

__all__ = ["RenodeCodeGenerator"]


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RenodeCodeGenerator(BaseCodeGenerator):
    """Generates a Renode simulation project (``device.repl`` + ``test_device.py``).

    The generator walks the parsed device model, resolves the board to a
    Renode platform description name (via :class:`BoardNameRegistry`), and
    renders the two artifacts through the ``renode/`` Jinja2 templates.
    The ``.repl`` script includes a guarded I2C memory-tag block that is
    only emitted when at least one peripheral is connected over I2C; the
    ``test_device.py`` driver adds a peripheral-presence test when the
    model declares any peripherals at all.
    """

    OS = "renode"

    def os_name(self) -> str:
        return self.OS

    def __init__(
        self,
        device_model,
        output_dir: Path,
        elf_path: Optional[str] = None,
    ):
        """Initialize code generator with device model.

        Args:
            device_model: Parsed textX device model.
            output_dir: Output directory for generated artifacts. Renode
                project files are written directly into ``<output_dir>/``
                (the simulator expects ``device.repl`` at the project
                root, mirroring the Wokwi project layout).
            elf_path: Optional path to a pre-built firmware ELF to embed
                in the rendered ``.repl`` script. When omitted, the
                template falls back to ``/tmp/firmware.elf`` so the
                rendered script remains a loadable artifact even without
                a pre-built firmware image.
        """
        super().__init__(device_model, output_dir)
        self.env = self.setup_template_environment()
        self._registry = BoardNameRegistry()
        # ``elf_path`` is forwarded from the CLI ``--elf-path`` flag; the
        # skeleton stored it but did not thread it into the context. The
        # Jinja templates consume it via the ``firmware_elf`` key.
        self._elf_path = elf_path

    def setup_template_environment(self) -> jinja2.Environment:
        """Setup Jinja2 environment with Renode-specific templates.

        ``trim_blocks``/``lstrip_blocks`` keep the rendered ``.repl`` and
        ``.py`` outputs tight (no stray whitespace from control tags).
        """
        fsloader = jinja2.FileSystemLoader(TEMPLATES_RENODE)
        return jinja2.Environment(
            loader=fsloader,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    def _resolve_board_name(self) -> str:
        """Resolve the model board to a Zephyr-style board identifier.

        Renode platform descriptions are conventionally named after the
        Zephyr board (e.g. ``esp32_devkitc``, ``rpi_4b``), so we reuse
        the Zephyr mapping from :class:`BoardNameRegistry` and fall back
        to the registry's lowercased name for unmapped boards. The
        template can override the value with ``board.zephyr_name`` if a
        per-board ``.hwd`` ``PLATFORMS`` block declares it.
        """
        board = self.get_board()
        return self._registry.resolve(board.name, "zephyr")

    def _board_context(self) -> Dict[str, Any]:
        """Build the ``board`` sub-context for the ``.repl`` template.

        The template expects ``board.os_arch`` (the Renode machine
        identifier) and ``board.zephyr_name`` (the platform description
        file basename). Both are derived from the DeMoL board name via
        :class:`BoardNameRegistry`; we expose them under a namespace
        so per-board ``PLATFORMS`` overrides remain a clean extension
        point without template-side conditional chains.
        """
        board = self.get_board()
        zephyr_name = self._resolve_board_name()
        # Derive a Renode machine identifier from the Zephyr board name.
        # ``esp32_devkitc`` -> ``esp32``; ``rpi_4b`` -> ``rpi_4b``; this
        # is the convention used by the upstream Renode platform
        # descriptions, so the default keeps the rendered script loadable
        # against stock Renode installations.
        os_arch = self._renode_arch(zephyr_name)
        return {
            "name": board.name,
            "os_arch": os_arch,
            "zephyr_name": zephyr_name,
        }

    @staticmethod
    def _renode_arch(zephyr_name: str) -> str:
        """Map a Zephyr board name to the Renode machine arch token.

        Defaults to ``esp32`` (the most common target in DeMoL's ESP
        example set) when the board does not match a known prefix; the
        Jinja template also defaults to ``esp32`` so an unmapped board
        still produces a loadable ``.repl`` script.
        """
        if zephyr_name.startswith("esp32"):
            return "esp32"
        if zephyr_name.startswith("esp8266"):
            return "esp32"  # Renode uses the esp32 machine for esp8266 firmware
        if zephyr_name.startswith("rpi"):
            return "rpi4b"
        return "esp32"

    def _collect_peripherals(self) -> List[Dict[str, Any]]:
        """Build the ``peripherals`` list for the test script template.

        Each entry is a ``{"name", "type"}`` dict; the test script
        template uses ``peripherals | length`` to decide whether to
        emit the per-peripheral presence test. The list is empty for
        board-only models (``USE`` with no ``CONNECT`` block), in which
        case the test script collapses to a single ``test_<name>_loads``
        function and the ``import time`` line is omitted.
        """
        peripherals: List[Dict[str, Any]] = []
        for conn in self.get_connections():
            periph = getattr(conn, "peripheral", None)
            if periph is None:
                continue
            instance_name = getattr(periph, "name", None) or type(periph.ref).__name__
            type_name = type(periph.ref).__name__ if hasattr(periph, "ref") else "Unknown"
            peripherals.append(
                {
                    "name": instance_name,
                    "type": type_name,
                }
            )
        return peripherals

    def _has_i2c(self) -> bool:
        """Return ``True`` if any connection uses the I2C data protocol.

        Used by the ``.repl`` template to emit the I2C memory-tag block
        that the Renode esp32 platform description expects. Walking
        ``dataConns`` is consistent with the Wokwi generator's protocol
        detection (see ``m2t_wokwi._build_global_context``).
        """
        for conn in self.get_connections():
            for data_conn in getattr(conn, "dataConns", []) or []:
                if getattr(data_conn, "type", None) == "i2c":
                    return True
        return False

    def build_global_context(self) -> Dict[str, Any]:
        """Build the global Jinja context for Renode templates.

        Returns:
            Dict with keys ``device_name``, ``board`` (sub-dict with
            ``os_arch``/``zephyr_name``), ``has_i2c`` (bool), ``peripherals``
            (list of ``{"name", "type"}`` dicts) and ``firmware_elf``
            (path to the pre-built firmware ELF, or ``None`` to use the
            template's default of ``/tmp/firmware.elf``).
        """
        device_name = self.device_model.metadata.name
        return {
            "device_name": device_name,
            "board": self._board_context(),
            "has_i2c": self._has_i2c(),
            "peripherals": self._collect_peripherals(),
            "firmware_elf": self._elf_path,
        }

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self) -> None:
        """Render ``device.repl`` and ``test_device.py`` for the device model.

        Both files are written at the root of ``output_dir`` because the
        Renode simulator expects the platform description script at the
        project root (mirrors the Wokwi project layout). The
        ``test_device.py`` driver is self-contained — it imports
        ``pyrenode3`` lazily inside the test function so the module
        remains parseable even when the optional test runtime is not
        installed in the generator's host environment.
        """
        logger.info("Generating Renode simulation project...")
        context = self.build_global_context()

        # device.repl: Renode platform description + machine load script.
        # Rendered through Jinja2 so the board name, I2C tag, and firmware
        # ELF path come from the model, not a hard-coded skeleton.
        template = self.env.get_template("repl.j2")
        self._write_template(template, context, self.output_dir / "device.repl")

        # test_device.py: pyrenode3-based pytest driver. The template
        # emits an extra per-peripheral presence test when the model
        # declares any peripherals; for board-only models it stays a
        # single ``test_<name>_loads`` function.
        template = self.env.get_template("test_script.py.j2")
        self._write_template(template, context, self.output_dir / "test_device.py")

        logger.info("Renode code generation complete!")


def m2t_renode(model, output_dir=".", elf_path=None):
    """Transform a DeMoL device model object to a Renode simulation project.

    Args:
        model: Parsed textX device model.
        output_dir: Output directory for the generated Renode artifacts.
        elf_path: Optional path to a pre-built firmware ELF to embed in
            the Renode platform description for direct simulation boot.
            Forwarded from the CLI ``--elf-path`` flag; the template
            defaults to ``/tmp/firmware.elf`` when this is ``None``.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    generator = RenodeCodeGenerator(model, output_path, elf_path=elf_path)
    generator.generate()
