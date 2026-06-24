"""Model-to-Text transformation for Renode simulation projects.

This module transforms DeMoL device models into a Renode simulation project
skeleton. Renode (https://renode.io) is an instruction-set simulator
primarily used for embedded / IoT firmware bring-up; the generated project
is a minimal ``.repl`` script plus a ``test_device.py`` driver that uses
``pyrenode3`` to spawn the simulator in-process and load the script.

The generator emits two artifacts at the project root:

* ``device.repl``     — Renode platform description + machine load script.
* ``test_device.py`` — pytest-style driver that boots the REPL via
                       ``pyrenode3.Antmicro`` and asserts the machine loads.

The full board / peripheral rendering is added in a follow-up task
(3.2 — Renode templates). This skeleton is enough to validate the
end-to-end CLI plumbing (``demol generate renode <file>``), the
package layout (``demol/transformations/m2t_renode.py``), and the
existence of a Renode-targeting code path that does not require Renode
to be installed for generation to succeed.
"""

import logging
from pathlib import Path
from typing import Any, Dict

import jinja2

from demol.definitions import TEMPLATES_RENODE
from .base_generator import BaseCodeGenerator

__all__ = ["RenodeCodeGenerator"]


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Minimum-valid Renode platform load script. Rendered via str.format
# because the Renode template directory is intentionally empty until
# Task 3.2 lands the real per-board / per-peripheral templates.
_DEVICE_REPL_SKELETON = """\
using sysbus
mach create "{machine_name}"
machine LoadPlatformDescription @platforms/boards/{board_repl}
"""

# pyrenode3-based pytest driver. ``pyrenode3`` is a runtime test
# dependency, not a demol install requirement, so the generated module
# stays a plain Python file with no build-time coupling.
_TEST_DEVICE_SKELETON = '''\
"""Auto-generated Renode test script for DeMoL device."""
import pyrenode3
from pyrenode3 import Antmicro

def test_device_loads():
    with Antmicro() as ant:
        ant.load_repl("device.repl")
        assert True
'''


class RenodeCodeGenerator(BaseCodeGenerator):
    """Generates a Renode simulation project skeleton (``device.repl`` + ``test_device.py``).

    The skeleton emits a minimum-valid REPL script for the target board
    (currently hard-coded to the ``esp32`` platform pending the Renode
    platform mapping in Task 3.2) and a ``pyrenode3``-based pytest driver
    that loads the REPL in-process. Real peripheral / pin / broker
    rendering is implemented in a follow-up task — this generator
    exists to wire up the CLI, package layout, and ``OS = "renode"``
    classification that other backends already rely on.
    """

    OS = "renode"

    def os_name(self) -> str:
        return self.OS

    def __init__(self, device_model, output_dir: Path):
        """Initialize code generator with device model.

        Args:
            device_model: Parsed textX device model.
            output_dir: Output directory for generated artifacts. Renode
                project files are written directly into ``<output_dir>/``
                (the simulator expects ``device.repl`` at the project
                root, mirroring the Wokwi project layout).
        """
        super().__init__(device_model, output_dir)
        # Wire up the Jinja2 environment now so Task 3.2 only needs to
        # drop template files into demol/templates/renode/.
        self.env = self.setup_template_environment()

    def setup_template_environment(self) -> jinja2.Environment:
        """Setup Jinja2 environment with Renode-specific templates.

        ``trim_blocks``/``lstrip_blocks`` keep the rendered ``.repl`` and
        ``.py`` outputs tight (no stray whitespace from control tags)
        when the real Renode templates land in Task 3.2.
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

    def build_global_context(self) -> Dict[str, Any]:
        """Build the global Jinja context for Renode templates.

        The skeleton only needs the device name and a board identifier;
        the full peripheral / pin / broker context will be added in
        Task 3.2 alongside the real templates.
        """
        device_name = self.device_model.metadata.name
        return {
            "device_name": device_name,
            "machine_name": device_name,
            # Placeholder board platform — Task 3.2 maps the model's
            # board to a real Renode ``@platforms/boards/<name>.repl``.
            "board_repl": "esp32.repl",
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

        device_repl = _DEVICE_REPL_SKELETON.format(
            machine_name=context["machine_name"],
            board_repl=context["board_repl"],
        )
        (self.output_dir / "device.repl").write_text(device_repl, encoding="utf-8")

        (self.output_dir / "test_device.py").write_text(_TEST_DEVICE_SKELETON, encoding="utf-8")

        logger.info("Renode code generation complete!")


def m2t_renode(model, output_dir="."):
    """Transform a DeMoL device model object to a Renode simulation project.

    Args:
        model: Parsed textX device model.
        output_dir: Output directory for the generated Renode artifacts.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    generator = RenodeCodeGenerator(model, output_path)
    generator.generate()
