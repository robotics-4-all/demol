"""Model-to-Text transformation for Wokwi simulation diagrams.

This module provides functionality to transform DeMoL device models into
Wokwi-compatible simulation projects. The skeleton emits the minimum
viable artifacts (diagram.json and wokwi.toml) without requiring a
Wokwi account, token, or network call; per-peripheral part mappings,
connection coloring, and Jinja2 templates are added in subsequent tasks
(Wave 2B / Task 2.9+).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

import jinja2

from demol.definitions import TEMPLATES_WOKWI
from .base_generator import BaseCodeGenerator

__all__ = ["WokwiCodeGenerator"]


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Skeleton file contents emitted by the Wave 2A backend.
# These are static placeholders — Jinja2 rendering of board/peripheral
# part mappings and connection wiring is introduced in Task 2.9.
#
# diagram.json follows the minimum Wokwi diagram schema (see
# https://docs.wokwi.com/diagram-format). An empty parts/connections
# list is valid; the Wave 2B templates will populate them from the
# parsed DeMoL model.

_DIAGRAM_JSON: Dict[str, Any] = {
    "version": 1,
    "author": "demol",
    "editor": "wokwi",
    "parts": [],
    "connections": [],
}


_WOKWI_TOML = """\
[wokwi]
version = 1
"""


class WokwiCodeGenerator(BaseCodeGenerator):
    """Generates a Wokwi simulation project skeleton from a device model.

    Wave 2A skeleton: emits the minimum artifact set expected by
    Wokwi's CLI / web simulator (diagram.json + wokwi.toml). The
    board/peripheral part mapping, connection wiring, and Jinja2
    templates are added in subsequent tasks.
    """

    OS = "wokwi"

    def os_name(self) -> str:
        return self.OS

    def __init__(self, device_model, output_dir: Path):
        """Initialize code generator with device model.

        Args:
            device_model: Parsed textX device model.
            output_dir: Output directory for generated artifacts. Wokwi
                files are written directly into ``<output_dir>/`` (the
                simulator expects ``diagram.json`` and ``wokwi.toml`` at
                the project root, not in a subdirectory).
        """
        super().__init__(device_model, output_dir)
        self.env = self.setup_template_environment()

    def setup_template_environment(self) -> jinja2.Environment:
        """Setup Jinja2 environment with Wokwi-specific templates.

        Returns:
            Configured Jinja2 Environment. Currently empty; populated
            as Jinja2 templates are introduced in later tasks.
        """
        fsloader = jinja2.FileSystemLoader(TEMPLATES_WOKWI)
        return jinja2.Environment(loader=fsloader)

    def build_global_context(self) -> Dict[str, Any]:
        """Build the global Jinja context for Wokwi templates.

        Returns a minimal context for the skeleton. Expanded in
        Task 2.9 with board name, peripheral parts, and connection
        wiring payload.
        """
        return {
            "device_name": self.device_model.metadata.name,
        }

    def generate(self) -> None:
        """Emit the Wokwi simulation project skeleton.

        Writes the minimum artifact set expected by the Wokwi simulator:
            diagram.json   — wiring + parts (currently empty arrays)
            wokwi.toml     — project manifest with [wokwi] version
        """
        logger.info("Generating Wokwi simulation skeleton...")
        global_context = self.build_global_context()

        # Use the base helper for UTF-8 file writes so behaviour matches
        # the other backends (and to keep the regression gate happy).
        def _write(path: Path, content: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.debug(f"Generated: {path}")

        # diagram.json: pretty-printed so the output is human-readable
        # and so subsequent tasks (2.9) can diff templates against it.
        _write(
            self.output_dir / "diagram.json",
            json.dumps(_DIAGRAM_JSON, indent=2) + "\n",
        )

        # wokwi.toml: static manifest. The [.wokwi] version table is the
        # only required key per the Wokwi project format spec.
        _write(
            self.output_dir / "wokwi.toml",
            _WOKWI_TOML.format(**global_context),
        )

        logger.info("Wokwi skeleton code generation complete!")


def m2t_wokwi(model, output_dir="."):
    """Transform a DeMoL device model object to a Wokwi simulation skeleton.

    Args:
        model: Parsed textX device model.
        output_dir: Output directory for the generated Wokwi artifacts.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    generator = WokwiCodeGenerator(model, output_path)
    generator.generate()
